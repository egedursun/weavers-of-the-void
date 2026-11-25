import itertools
from dataclasses import dataclass
from itertools import pairwise

from sqlalchemy import select
from sqlalchemy.orm import aliased

from aerona.catalog.movement import FOOT_WAYS
from aerona.catalog.strata import STRATA
from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.biology import BiologyRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.couplings import DeepSealRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.geology import DeepPassageRow, PolityDeepKnowledgeRow, RegionStratumRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.geology import DeepPassageOrigin, DeepPassageState, UndergroundStratum
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction, StepLocus
from aerona.domain.models.entity_stats import SettlementStats
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import realm_of
from aerona.engine.demography.control import found_people
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.primitives.deep import Cell, Level, passage_kind, shape_fault
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.recording.terms import explaining_alone, term
from aerona.language.generator import NameKind
from aerona.rules.model import keyed
from aerona.rules.registry import Rules

TargetPart = aliased(IncidentParticipantRow)
CELLS_FIXUP = "underground.w52_cells"
PASSAGES_FIXUP = "underground.w52_passages"
PEOPLES_FIXUP = "underground.w52_peoples"
OPENING_SUBTYPES = ("cave", "cavern system", "cavern_system", "sinkhole")


@dataclass
class DeepTally:
    shaped: int = 0
    passages: int = 0
    dug: int = 0
    collapsed: int = 0
    flooded: int = 0
    drained: int = 0
    cleared: int = 0
    sealed: int = 0
    known: int = 0
    contacts: int = 0
    strained: int = 0
    peoples: int = 0
    narrowed: int = 0
    named: int = 0


def cell_light(rules: Rules, stratum: UndergroundStratum) -> int:
    return keyed(rules.underground, stratum.value, "light")


def shape_cell(rules: Rules, row: RegionStratumRow, ground: RegionEnvironmentRow | None, roll: int, realm: int | None) -> None:
    spec = STRATA[row.stratum]
    if "terrain" not in row.locked:
        row.terrain = ground.dominant_terrain if row.stratum is UndergroundStratum.HOLLOW_INTERIOR and ground is not None else spec.terrain
    if "light" not in row.locked:
        row.light = cell_light(rules, row.stratum)
    if "extent" not in row.locked:
        row.extent = clamp_int(rules.underground.extent_min + roll % (PERCENT - rules.underground.extent_min + 1), 1, PERCENT)
    if "realm_entity_id" not in row.locked and row.stratum is UndergroundStratum.DEEP_UNDERWORLD:
        row.realm_entity_id = realm


async def cells_by_region(ctx: TickContext) -> dict[int, dict[UndergroundStratum, RegionStratumRow]]:
    found: dict[int, dict[UndergroundStratum, RegionStratumRow]] = {}
    for row in await ctx.session.scalars(select(RegionStratumRow).order_by(RegionStratumRow.id)):
        found.setdefault(row.region_entity_id, {})[row.stratum] = row
    return found


async def underworld_of(ctx: TickContext, world_id: int) -> int | None:
    return await ctx.session.scalar(
        select(EntityRow.id).where(EntityRow.world_id == world_id, EntityRow.is_underworld.is_(True), EntityRow.status == EntityStatus.CANON).limit(1)
    )


async def shape_cells(ctx: TickContext, tally: DeepTally) -> None:
    if await ctx.session.get(AppliedFixupRow, CELLS_FIXUP) is not None:
        return
    for row in list(await ctx.session.scalars(select(RegionStratumRow).order_by(RegionStratumRow.id))):
        if held(row.region_entity_id):
            continue
        ground = await ctx.session.get(RegionEnvironmentRow, row.region_entity_id)
        realm = await underworld_of(ctx, ground.world_id) if ground is not None else None
        shape_cell(ctx.rules, row, ground, ctx.rng(f"cell.extent.{row.id}").below(PERCENT), realm)
        tally.shaped += 1
    ctx.session.add(AppliedFixupRow(key=CELLS_FIXUP, result={"shaped": tally.shaped}))
    await ctx.session.flush()


async def passage_between(ctx: TickContext, first: Cell, second: Cell) -> DeepPassageRow | None:
    low, high = sorted((first, second), key=lambda cell: (cell[0], cell[1].value if cell[1] is not None else ""))
    return await ctx.session.scalar(
        select(DeepPassageRow).where(
            DeepPassageRow.first_region_entity_id == low[0],
            DeepPassageRow.first_stratum.is_(None) if low[1] is None else DeepPassageRow.first_stratum == low[1],
            DeepPassageRow.second_region_entity_id == high[0],
            DeepPassageRow.second_stratum.is_(None) if high[1] is None else DeepPassageRow.second_stratum == high[1],
        )
    )


async def make_passage(
    ctx: TickContext,
    world_id: int,
    first: Cell,
    second: Cell,
    *,
    origin: DeepPassageOrigin,
    state: DeepPassageState = DeepPassageState.OPEN,
    place_id: int | None = None,
    digger_id: int | None = None,
    by_node_id: int | None = None,
) -> DeepPassageRow:
    found = await passage_between(ctx, first, second)
    if found is not None:
        return found
    low, high = sorted((first, second), key=lambda cell: (cell[0], cell[1].value if cell[1] is not None else ""))
    digging = state is DeepPassageState.DIGGING
    row = DeepPassageRow(
        world_id=world_id,
        first_region_entity_id=low[0],
        first_stratum=low[1],
        second_region_entity_id=high[0],
        second_stratum=high[1],
        state=state,
        origin=origin,
        width=ctx.rules.underground.narrow_width + PERCENT // 4,
        progress=0 if digging else PERCENT,
        opened=not digging,
        place_entity_id=place_id,
        dug_by_entity_id=digger_id,
        by_node_id=by_node_id,
        created_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


def shallowest_dwelling(cells: dict[UndergroundStratum, RegionStratumRow]) -> RegionStratumRow | None:
    for stratum in STRATA:
        row = cells.get(stratum)
        if row is not None and STRATA[stratum].dwellable:
            return row
    return None


async def lay_natural_passages(ctx: TickContext, tally: DeepTally) -> None:
    if await ctx.session.get(AppliedFixupRow, PASSAGES_FIXUP) is not None:
        return
    table = ctx.rules.underground
    atlas = await RegionAtlas.load(ctx.session)
    cells = await cells_by_region(ctx)
    for region_id, below in sorted(cells.items()):
        world_id = atlas.world_of(region_id)
        if world_id is None or held(region_id):
            continue
        for other in atlas.neighbours(region_id):
            if other <= region_id or other not in cells or held(other):
                continue
            for stratum in sorted(set(below) & set(cells[other]), key=lambda value: value.value):
                if ctx.rng(f"deep.level.{region_id}.{other}.{stratum.value}").chance(table.natural_level_pct):
                    await make_passage(ctx, world_id, (region_id, stratum), (other, stratum), origin=DeepPassageOrigin.NATURAL)
                    tally.passages += 1
        dwellable = [stratum for stratum in STRATA if stratum in below and STRATA[stratum].dwellable]
        for upper, lower in itertools.pairwise(dwellable):
            if ctx.rng(f"deep.vertical.{region_id}.{upper.value}").chance(table.natural_vertical_pct):
                await make_passage(ctx, world_id, (region_id, upper), (region_id, lower), origin=DeepPassageOrigin.NATURAL)
                tally.passages += 1
        shallow = shallowest_dwelling(below)
        if shallow is None:
            continue
        caves = await ctx.session.scalars(
            select(EntityRow.id)
            .where(EntityRow.location_id == region_id, EntityRow.entity_type == EntityType.PLACE, EntityRow.subtype.in_(OPENING_SUBTYPES))
            .order_by(EntityRow.id)
        )
        for cave in list(caves):
            if ctx.rng(f"deep.opening.{cave}").chance(table.natural_opening_pct):
                await make_passage(ctx, world_id, (region_id, None), (region_id, shallow.stratum), origin=DeepPassageOrigin.NATURAL, place_id=cave)
                tally.passages += 1
                break
    ctx.session.add(AppliedFixupRow(key=PASSAGES_FIXUP, result={"passages": tally.passages}))
    await ctx.session.flush()


def ends_of(row: DeepPassageRow) -> tuple[Cell, Cell]:
    return (row.first_region_entity_id, row.first_stratum), (row.second_region_entity_id, row.second_stratum)


async def tell(ctx: TickContext, key: str, row: DeepPassageRow, actor: int | None = None) -> None:
    first, second = ends_of(row)
    roles = {IncidentRole.PLACE: first[0], IncidentRole.DESTINATION: second[0], **({IncidentRole.ACTOR: actor} if actor is not None else {})}
    await record(
        ctx,
        key,
        roles=roles,
        facts={"kind": passage_kind(first, second), "state": row.state, "origin": row.origin},
        place=first[0],
        steps=(
            StepDraft(StepAction.ENTER, actor=actor, locus_kind=StepLocus.STRATUM, locus_key=(second[1] or first[1] or UndergroundStratum.CAVERN_UPPER).value),
        ),
    )


async def open_the_way_down(
    ctx: TickContext,
    ground: RegionEnvironmentRow,
    stratum: UndergroundStratum,
    *,
    origin: DeepPassageOrigin = DeepPassageOrigin.DUG,
    digger_id: int | None = None,
    by_node_id: int | None = None,
) -> DeepPassageRow | None:
    region = ground.entity_id
    if held(region) or await passage_between(ctx, (region, None), (region, stratum)) is not None:
        return None
    row = await make_passage(ctx, ground.world_id, (region, None), (region, stratum), origin=origin, digger_id=digger_id, by_node_id=by_node_id)
    await tell(ctx, "deep.passage_formed", row, by_node_id if by_node_id is not None else digger_id)
    return row


async def sealed_passages(ctx: TickContext) -> set[int]:
    return {
        passage
        for passage in await ctx.session.scalars(select(DeepSealRow.passage_id).where(DeepSealRow.passage_id.is_not(None), DeepSealRow.broken_epoch.is_(None)))
        if passage is not None
    }


def beside_water(cells: dict[int, dict[UndergroundStratum, RegionStratumRow]], first: Cell, second: Cell) -> bool:
    return any(UndergroundStratum.AQUIFER in cells.get(cell[0], {}) for cell in (first, second))


def stressed(cells: dict[int, dict[UndergroundStratum, RegionStratumRow]], first: Cell, second: Cell) -> bool:
    return any(UndergroundStratum.FAULT_ZONE in cells.get(cell[0], {}) for cell in (first, second))


async def live_passages(ctx: TickContext, tally: DeepTally) -> None:
    table = ctx.rules.underground
    cells = await cells_by_region(ctx)
    sealed = await sealed_passages(ctx)
    drain_pct = PERCENT // max(1, table.epochs(table.drain_years))
    for row in list(await ctx.session.scalars(select(DeepPassageRow).order_by(DeepPassageRow.id))):
        first, second = ends_of(row)
        if held(first[0], second[0]) or "state" in row.locked:
            continue
        rng = ctx.rng(f"deep.passage.{row.id}.{ctx.epoch}")
        if row.id in sealed and row.state is not DeepPassageState.SEALED:
            row.state = DeepPassageState.SEALED
            tally.sealed += 1
            await tell(ctx, "deep.passage_sealed", row)
        elif row.id not in sealed and row.state is DeepPassageState.SEALED:
            row.state = DeepPassageState.OPEN
        elif row.state is DeepPassageState.DIGGING and "progress" not in row.locked:
            row.progress = clamp_int(row.progress + table.dig_rate, 0, PERCENT)
            if row.progress >= PERCENT:
                row.state, row.opened = DeepPassageState.OPEN, True
                tally.dug += 1
                await tell(ctx, "deep.passage_dug", row, row.dug_by_entity_id)
        elif row.state is DeepPassageState.COLLAPSED and row.dug_by_entity_id is not None and "progress" not in row.locked:
            row.progress = clamp_int(row.progress + table.clear_rate, 0, PERCENT)
            if row.progress >= PERCENT:
                row.state = DeepPassageState.OPEN
                tally.cleared += 1
                await tell(ctx, "deep.passage_cleared", row, row.dug_by_entity_id)
        elif row.state is DeepPassageState.FLOODED and rng.chance(drain_pct):
            row.state = DeepPassageState.OPEN
            tally.drained += 1
            await tell(ctx, "deep.passage_drained", row)
        elif row.state is DeepPassageState.OPEN and rng.chance(table.collapse_pct * (2 if stressed(cells, first, second) else 1)):
            row.state, row.progress = DeepPassageState.COLLAPSED, 0
            tally.collapsed += 1
            await tell(ctx, "deep.passage_collapsed", row)
        elif row.state is DeepPassageState.OPEN and beside_water(cells, first, second) and rng.chance(table.flood_pct):
            row.state = DeepPassageState.FLOODED
            tally.flooded += 1
            await tell(ctx, "deep.passage_flooded", row)


async def dig_toward(ctx: TickContext, digger: EntityRow, first: Cell, second: Cell, *, by_node_id: int | None = None) -> DeepPassageRow:
    atlas = await RegionAtlas.load(ctx.session)
    fault = shape_fault(first, second, second[0] in atlas.neighbours(first[0]))
    if fault is not None:
        raise ValueError(fault)
    found = await passage_between(ctx, first, second)
    if found is not None:
        return found
    world_id = atlas.world_of(first[0]) or digger.world_id
    return await make_passage(
        ctx, world_id, first, second, origin=DeepPassageOrigin.DUG, state=DeepPassageState.DIGGING, digger_id=digger.id, by_node_id=by_node_id
    )


async def breach_opening(ctx: TickContext, mine: EntityRow, beast: EntityRow | None) -> DeepPassageRow | None:
    atlas = await RegionAtlas.load(ctx.session)
    region = atlas.top_region(mine.id)
    if region is None or held(region):
        return None
    below = (await cells_by_region(ctx)).get(region, {})
    shallow = shallowest_dwelling(below)
    if shallow is None:
        return None
    row = await passage_between(ctx, (region, None), (region, shallow.stratum))
    if row is None:
        row = await make_passage(
            ctx, atlas.world_of(region) or mine.world_id, (region, None), (region, shallow.stratum), origin=DeepPassageOrigin.BREACH, place_id=mine.id
        )
        await tell(ctx, "deep.passage_formed", row)
    if beast is not None and not held(beast.id):
        beast.location_id, beast.stratum = region, shallow.stratum
        atlas.remember(beast)
    return row


async def polity_of(ctx: TickContext, town_id: int) -> int | None:
    return await realm_of(ctx.session, town_id)


async def know_cells(ctx: TickContext, tally: DeepTally) -> None:
    table = ctx.rules.underground
    atlas = await RegionAtlas.load(ctx.session)
    cells = await cells_by_region(ctx)
    towns = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.stratum.is_not(None))
        .order_by(EntityRow.id)
    )
    for town in list(towns):
        cell = atlas.cell_of(town.id)
        if cell is None or cell[1] is None:
            continue
        realm = await polity_of(ctx, town.id) or town.id
        row = cells.get(cell[0], {}).get(cell[1])
        if row is None or held(realm):
            continue
        known = await ctx.session.get(PolityDeepKnowledgeRow, (realm, row.id))
        if known is None:
            known = PolityDeepKnowledgeRow(polity_entity_id=realm, cell_id=row.id, level=0, held=True, updated_epoch=ctx.epoch, locked=[])
            ctx.session.add(known)
            tally.known += 1
        if "level" not in known.locked:
            known.level = clamp_int(known.level + table.knowledge_per_crossing, 0, PERCENT)
        if "held" not in known.locked:
            known.held = True
        known.updated_epoch = ctx.epoch
    await ctx.session.flush()


def cell_region(atlas: RegionAtlas, town: EntityRow) -> int:
    return atlas.top_region(town.id) or town.location_id or town.id


async def strain_unadapted(ctx: TickContext, tally: DeepTally) -> None:
    table = ctx.rules.underground
    atlas = await RegionAtlas.load(ctx.session)
    towns = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.stratum.is_not(None))
        .order_by(EntityRow.id)
    )
    for town in list(towns):
        level: Level = atlas.level_of(town.id)
        if level is None or held(town.id):
            continue
        folk = await people_of(ctx.session, town)
        biology = await ctx.session.get(BiologyRow, folk.id) if folk is not None else None
        if biology is not None and set(biology.variants) & {variant.value for variant in STRATA[level].adapted}:
            continue
        if stat_or(town, "prosperity", 0) < table.flee_prosperity and atlas.cell_path(
            (cell_region(atlas, town), level), (cell_region(atlas, town), None), FOOT_WAYS
        ):
            town.stratum = None
            atlas.remember(town)
            await record(
                ctx,
                "deep.migrated",
                roles={IncidentRole.ACTOR: folk.id if folk is not None else town.id, IncidentRole.PLACE: cell_region(atlas, town)},
                facts={"stratum": level},
                place=cell_region(atlas, town),
            )
            continue
        with explaining_alone():
            term("underground.unadapted_penalty_pct", -table.unadapted_penalty_pct / 10, source_node_id=town.id)
            shift_stat(town, "prosperity", -table.unadapted_penalty_pct / 10, low=0, high=PERCENT)
        tally.strained += 1


async def meet_below(ctx: TickContext, tally: DeepTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    towns = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )
    below = [town for town in towns if atlas.level_of(town.id) is not None]
    if not below:
        return
    met = {
        f"{min(actor, target)}.{max(actor, target)}"
        for actor, target in (
            await ctx.session.execute(
                select(IncidentParticipantRow.node_id, TargetPart.node_id)
                .join(IncidentRow, IncidentRow.id == IncidentParticipantRow.incident_id)
                .join(TargetPart, TargetPart.incident_id == IncidentRow.id)
                .where(IncidentRow.kind == "deep.contact", IncidentParticipantRow.role == IncidentRole.ACTOR, TargetPart.role == IncidentRole.TARGET)
            )
        ).all()
    }
    for deep in below:
        for other in towns:
            if (
                other.id == deep.id
                or other.affiliated_entity_id == deep.affiliated_entity_id
                or other.affiliated_entity_id is None
                or deep.affiliated_entity_id is None
            ):
                continue
            pair = sorted((deep.affiliated_entity_id, other.affiliated_entity_id))
            key = f"{pair[0]}.{pair[1]}"
            if key in met or held(deep.id, other.id) or not atlas.adjacent(deep.id, other.id):
                continue
            met.add(key)
            tally.contacts += 1
            await record(
                ctx,
                "deep.contact",
                roles={IncidentRole.ACTOR: deep.affiliated_entity_id, IncidentRole.TARGET: other.affiliated_entity_id, IncidentRole.PLACE: deep.id},
                facts={"stratum": atlas.level_of(deep.id) or UndergroundStratum.CAVERN_UPPER},
                place=deep.id,
            )


async def found_below(ctx: TickContext, region: EntityRow, world_id: int, label: str, *, depth: str, founders: int) -> tuple[EntityRow, EntityRow]:
    people = await found_people(ctx, name=f"Folk of the {label}", region_id=region.id, population=founders, species_id=None, language_id=None, values={})
    town = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.SETTLEMENT,
            name=f"Home of the {label}",
            body=f"The first home of {people.name}, in the {depth} beneath {region.name}.",
            stats=SettlementStats(population=founders, prosperity=PERCENT // 3, defense=PERCENT // 3, piety=PERCENT // 2),
            power=1,
            location_id=region.id,
            world_id=world_id,
            subtype="homeland",
        ),
    )
    return people, town


async def seed_deep_peoples(ctx: TickContext, tally: DeepTally) -> None:
    if await ctx.session.get(AppliedFixupRow, PEOPLES_FIXUP) is not None:
        return
    table = ctx.rules.underground
    atlas = await RegionAtlas.load(ctx.session)
    peopled = {(atlas.top_region(town.id), town.stratum) for town in await ctx.session.scalars(select(EntityRow).where(EntityRow.stratum.is_not(None)))}
    by_world: dict[int, dict[UndergroundStratum, list[RegionStratumRow]]] = {}
    for region_id, below in (await cells_by_region(ctx)).items():
        world_id = atlas.world_of(region_id)
        if world_id is None or held(region_id):
            continue
        for stratum, row in below.items():
            if STRATA[stratum].dwellable and (region_id, stratum) not in peopled:
                by_world.setdefault(world_id, {}).setdefault(stratum, []).append(row)
    for world_id, strata in sorted(by_world.items()):
        for stratum, rows in sorted(strata.items(), key=lambda item: item[0].value):
            if not ctx.rng(f"deep.people.{world_id}.{stratum.value}").chance(table.people_pct):
                continue
            cell = max(rows, key=lambda row: (row.extent, -row.id))
            region = await ctx.session.get(EntityRow, cell.region_entity_id)
            if region is None:
                continue
            label = cell.name or f"{STRATA[stratum].label} beneath {region.name}"
            with flowing(FlowCategory.CREATION):
                people, town = await found_below(ctx, region, world_id, label, depth=STRATA[stratum].label.lower(), founders=table.people_founders)
            people.stratum = stratum
            town.stratum = stratum
            await connect(ctx.session, town.id, people.id, BondKind.DESCENDS_FROM, ctx.epoch)
            await BondRepository(ctx.session).connect(BondDraft(people.id, town.id, BondKind.RULES, ctx.epoch, "own people's homeland", role=BondRole.HOMELAND))
            tally.peoples += 1
            await record(
                ctx,
                "deep.settled",
                roles={IncidentRole.ACTOR: people.id, IncidentRole.PRODUCT: town.id, IncidentRole.PLACE: region.id},
                facts={"stratum": stratum},
                place=region.id,
            )
    ctx.session.add(AppliedFixupRow(key=PEOPLES_FIXUP, result={"peoples": tally.peoples}))
    await ctx.session.flush()


async def level_for(ctx: TickContext, atlas: RegionAtlas, people: EntityRow, region_id: int) -> UndergroundStratum | None:
    home = atlas.level_of(people.id) if people.stratum is None else people.stratum
    below = (await cells_by_region(ctx)).get(region_id, {})
    if home is not None:
        return home if home in below else None
    crowded = len(atlas.communities_in(region_id)) >= ctx.rules.underground.crowded_communities
    known = [row for stratum, row in below.items() if STRATA[stratum].dwellable and await known_by(ctx, people, row)]
    if not crowded or not known:
        return None
    cell = max(known, key=lambda row: (row.extent, -row.id))
    return cell.stratum if ctx.rng(f"deep.settle.{people.id}.{region_id}.{ctx.epoch}").chance(cell.extent) else None


async def known_by(ctx: TickContext, people: EntityRow, cell: RegionStratumRow) -> bool:
    realm = await realm_of(ctx.session, people.id) or people.id
    row = await ctx.session.get(PolityDeepKnowledgeRow, (realm, cell.id))
    return row is not None and row.level >= ctx.rules.underground.knowledge_per_crossing


async def light_below(ctx: TickContext, entity: EntityRow) -> float:
    atlas = await RegionAtlas.load(ctx.session)
    cell = atlas.cell_of(entity.id)
    if cell is None or cell[1] is None:
        return 1.0
    row = (await cells_by_region(ctx)).get(cell[0], {}).get(cell[1])
    folk = await people_of(ctx.session, entity)
    biology = await ctx.session.get(BiologyRow, folk.id) if folk is not None else None
    if row is None or (biology is not None and set(biology.variants) & {variant.value for variant in STRATA[cell[1]].adapted}):
        return 1.0
    return row.light / PERCENT


async def march_below(ctx: TickContext, tally: DeepTally) -> None:
    table = ctx.rules.underground
    atlas = await RegionAtlas.load(ctx.session)
    for profile in list(await ctx.session.scalars(select(ArmyProfileRow).order_by(ArmyProfileRow.army_entity_id))):
        cell = atlas.cell_of(profile.army_entity_id)
        if cell is None or held(profile.army_entity_id) or "stratum" in profile.locked:
            continue
        before: Cell = (profile.region_entity_id or cell[0], profile.stratum)
        if before == cell or before[1] is cell[1]:
            continue
        route = atlas.cell_path(before, cell) or []
        narrow = False
        for first, second in pairwise(route):
            passage = await passage_between(ctx, first, second) if first[0] == second[0] or first[1] is not None else None
            narrow = narrow or (passage is not None and passage.width < table.narrow_width)
        if narrow and "cohesion" not in profile.locked:
            with explaining_alone():
                term("underground.narrow_army_pct", profile.cohesion * (table.narrow_army_pct - PERCENT) / PERCENT, source_node_id=profile.army_entity_id)
                profile.cohesion = clamp_int(profile.cohesion * table.narrow_army_pct // PERCENT, 0, PERCENT)
            tally.narrowed += 1
        profile.stratum = cell[1]


async def name_cells(ctx: TickContext, tally: DeepTally) -> None:
    namer = Namer(ctx.session, ctx.rules)
    for row in list(await ctx.session.scalars(select(RegionStratumRow).where(RegionStratumRow.name.is_(None)).order_by(RegionStratumRow.id))):
        if held(row.region_entity_id) or "name" in row.locked or not STRATA[row.stratum].dwellable:
            continue
        ground = await ctx.session.get(RegionEnvironmentRow, row.region_entity_id)
        if ground is None:
            continue
        row.name = await namer.for_world(ground.world_id, seed_of("cell", row.id), NameKind.PLACE)
        tally.named += int(row.name is not None)


async def keep_the_deep(ctx: TickContext) -> DeepTally:
    tally = DeepTally()
    await shape_cells(ctx, tally)
    await name_cells(ctx, tally)
    await lay_natural_passages(ctx, tally)
    await seed_deep_peoples(ctx, tally)
    await live_passages(ctx, tally)
    await know_cells(ctx, tally)
    await strain_unadapted(ctx, tally)
    await meet_below(ctx, tally)
    await march_below(ctx, tally)
    await ctx.session.flush()
    return tally
