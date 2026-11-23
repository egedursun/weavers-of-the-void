from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.museums import GARDEN_LIFE, GARDEN_WILD, GATHERING_GARDENS, PLANTING_SPECIES_CLASSS
from aerona.constants.units import PERCENT
from aerona.db.tables.agrarian import GameReserveRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gardens import GardenRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.garden import GardenKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import domains_of, faithful_communities, living_gods
from aerona.engine.divine.standing import standing_row
from aerona.engine.economy.purse import take_coin
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import branch_level
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.recording.record import record

LAID_OUT = {
    StructureKind.PARK: GardenKind.PARK,
    StructureKind.BOTANICAL_GARDEN: GardenKind.PHYSIC,
    StructureKind.CEMETERY: GardenKind.CEMETERY,
    StructureKind.MONASTERY: GardenKind.MONASTERY,
    StructureKind.MENAGERIE: GardenKind.MENAGERIE,
}
GROWING = frozenset({Domain.PLANTS, Domain.LIFE, Domain.HARVEST, Domain.HUNT})
PLANTED = GARDEN_LIFE
ESCAPED_ABUNDANCE = 5


@dataclass
class GardenTally:
    founded: int = 0
    tended: int = 0
    neglected: int = 0
    loved: int = 0


async def known_gardens(ctx: TickContext) -> set[tuple[int, GardenKind]]:
    return {(row.settlement_entity_id, row.kind) for row in await ctx.session.scalars(select(GardenRow))}


async def lay_out(ctx: TickContext, town_id: int, kind: GardenKind, structure_id: int | None, atlas: RegionAtlas) -> GardenRow:
    table = ctx.rules.gardens
    row = GardenRow(
        settlement_entity_id=town_id,
        structure_entity_id=structure_id,
        kind=kind,
        species=await planting(ctx, atlas, town_id, kind),
        upkeep=table.upkeep,
        condition=table.condition,
        founded_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await record(ctx, "garden.founded", roles={IncidentRole.PLACE: town_id}, facts={"kind": kind}, place=town_id)
    return row


async def planting(ctx: TickContext, atlas: RegionAtlas, town_id: int, kind: GardenKind) -> list[int]:
    region = atlas.top_region(town_id)
    if region is None:
        return []
    classes = PLANTED.get(kind, PLANTING_SPECIES_CLASSS)
    lands = [region, *atlas.neighbours(region)] if kind in GATHERING_GARDENS else [region]
    found = await ctx.session.scalars(
        select(SpeciesRangeRow.species_entity_id)
        .join(SpeciesProfileRow, SpeciesProfileRow.species_entity_id == SpeciesRangeRow.species_entity_id)
        .where(SpeciesRangeRow.region_entity_id.in_(lands), SpeciesRangeRow.abundance > 0, SpeciesProfileRow.species_class.in_(list(classes)))
        .order_by(SpeciesRangeRow.abundance.desc(), SpeciesRangeRow.species_entity_id)
        .limit(ctx.rules.gardens.planted * (2 if kind in GATHERING_GARDENS else 1))
    )
    return list(dict.fromkeys(int(item) for item in found))


async def towns_in(ctx: TickContext, atlas: RegionAtlas, region_id: int) -> list[EntityRow]:
    towns = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    return [town for town in towns if atlas.top_region(town.id) == region_id]


async def found_gardens(ctx: TickContext, atlas: RegionAtlas, tally: GardenTally) -> None:
    known = await known_gardens(ctx)
    wanted: list[tuple[int, GardenKind, int | None]] = []
    for structure_id, host_id, hall in await ctx.session.execute(
        select(StructureProfileRow.structure_entity_id, StructureProfileRow.host_entity_id, StructureProfileRow.kind).where(
            StructureProfileRow.kind.in_(list(LAID_OUT)), StructureProfileRow.host_entity_id.is_not(None)
        )
    ):
        if host_id is not None:
            wanted.append((host_id, LAID_OUT[hall], structure_id))
    groves = await ctx.session.execute(
        select(EntityRow.location_id).join(PlaceProfileRow, PlaceProfileRow.entity_id == EntityRow.id).where(PlaceProfileRow.kind == PlaceKind.GROVE)
    )
    for (place_region,) in groves.all():
        for town in await towns_in(ctx, atlas, place_region) if place_region is not None else []:
            wanted.append((town.id, GardenKind.SACRED_GROVE, None))
    for reserve_region in sorted(set(await ctx.session.scalars(select(GameReserveRow.region_entity_id)))):
        near = await towns_in(ctx, atlas, reserve_region)
        if near:
            seat = max(near, key=lambda town: (stat_or(town, "population", 0), -town.id))
            wanted.append((seat.id, GardenKind.HUNTING_PARK, None))
    for town in await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    ):
        if stat_or(town, "prosperity", 0) >= ctx.rules.gardens.pleasure_from:
            wanted.append((town.id, GardenKind.PLEASURE, None))
            if await branch_level(ctx.session, town.id, KnowledgeBranch.AGRICULTURE) >= ctx.rules.gardens.botanic_from:
                wanted.append((town.id, GardenKind.BOTANIC, None))
    for town_id, garden_kind, hall_id in wanted:
        if (town_id, garden_kind) in known or held(town_id):
            continue
        await lay_out(ctx, town_id, garden_kind, hall_id, atlas)
        known.add((town_id, garden_kind))
        tally.founded += 1


async def tend(ctx: TickContext, garden: GardenRow, tally: GardenTally) -> None:
    table = ctx.rules.gardens
    town = await ctx.session.get(EntityRow, garden.settlement_entity_id)
    if town is None or town.status is not EntityStatus.CANON:
        return
    paid = await take_coin(ctx.session, ctx.rules, town, garden.upkeep)
    if "condition" not in garden.locked:
        garden.condition = clamp_int(garden.condition + (table.tended if paid else -table.neglect), 0, PERCENT)
    garden.unpaid_epochs = 0 if paid else garden.unpaid_epochs + 1
    tally.tended += int(paid)
    tally.neglected += int(not paid)


async def love_groves(ctx: TickContext, tally: GardenTally) -> None:
    groves = list(await ctx.session.scalars(select(GardenRow).where(GardenRow.kind == GardenKind.SACRED_GROVE, GardenRow.condition > 0)))
    if not groves:
        return
    towns = {garden.settlement_entity_id for garden in groves}
    for god in await living_gods(ctx.session):
        if not set(domains_of(god)) & GROWING or held(god.id):
            continue
        faithful = {community.id for community in await faithful_communities(ctx.session, god.id)}
        for town_id in sorted(towns & faithful):
            if held(town_id):
                continue
            row = await standing_row(ctx, town_id, god.id)
            if "love" not in row.locked:
                row.love = clamp_int(row.love + ctx.rules.gardens.grove_standing, 0, PERCENT)
                tally.loved += 1


async def study(ctx: TickContext, garden: GardenRow) -> None:
    lore = await ctx.session.scalar(
        select(EntityRow)
        .join(BondRow, BondRow.target_node_id == EntityRow.id)
        .where(
            BondRow.source_node_id == garden.settlement_entity_id,
            BondRow.kind == BondKind.KNOWS,
            BondRow.state == BondState.ACTIVE,
            EntityRow.knowledge_branch == KnowledgeBranch.AGRICULTURE,
        )
        .order_by(EntityRow.id)
        .limit(1)
    )
    if lore is not None and not held(lore.id):
        shift_stat(lore, "spread", ctx.rules.gardens.botanic_knowledge * garden.condition // PERCENT)


async def let_loose(ctx: TickContext, atlas: RegionAtlas, garden: GardenRow) -> int:
    region = atlas.top_region(garden.settlement_entity_id)
    if region is None or garden.unpaid_epochs <= 0 or held(region):
        return 0
    if not ctx.rng(f"menagerie.{garden.id}.{ctx.epoch}").chance(ctx.rules.gardens.menagerie_escape_pct):
        return 0
    loosed = 0
    for species_id in garden.species:
        if await ctx.session.get(SpeciesRangeRow, (species_id, region)) is None:
            ctx.session.add(
                SpeciesRangeRow(species_entity_id=species_id, region_entity_id=region, abundance=ESCAPED_ABUNDANCE, since_epoch=ctx.epoch, locked=[])
            )
            loosed += 1
    if loosed:
        await record(
            ctx, "garden.beasts_loosed", roles={IncidentRole.PLACE: garden.settlement_entity_id}, facts={"kinds": loosed}, place=garden.settlement_entity_id
        )
    return loosed


async def keep_gardens(ctx: TickContext, tally: GardenTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    await found_gardens(ctx, atlas, tally)
    for garden in list(await ctx.session.scalars(select(GardenRow).order_by(GardenRow.id))):
        if held(garden.settlement_entity_id):
            continue
        await tend(ctx, garden, tally)
        if garden.kind in GATHERING_GARDENS and garden.condition > 0 and not GARDEN_WILD[garden.kind]:
            await study(ctx, garden)
        elif GARDEN_WILD[garden.kind]:
            await let_loose(ctx, atlas, garden)
    await love_groves(ctx, tally)
    await ctx.session.flush()
