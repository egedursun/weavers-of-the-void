from collections import defaultdict
from dataclasses import dataclass, field
from types import MappingProxyType

from sqlalchemy import delete, select

from aerona.constants.units import PERCENT
from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.dominion import SCALE_MAX, SCALE_MIN, DominionRow, GodScaleRow, MiracleRecordRow, RegionDominionRow, ThroneRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.faith import CultHoldingRow
from aerona.db.tables.interconnect import ModifierRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.dominion import DivineScale
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.mind import ThoughtKind
from aerona.domain.enums.modifier import IncidentRole, ModifierOp, ModifierSource
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.dominion.book import DominionBook
from aerona.engine.dominion.design import ensure_designs
from aerona.engine.mind.thoughts import think
from aerona.engine.mortal.standing import add_stress
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.modifiers import GROWTH_KEY, ModifierDraft, add_modifier
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record

PREFIX = "dominion."
CLERGY = (MortalRole.PRIEST, MortalRole.SAINT, MortalRole.SEER)
COLUMNS = ("temples", "holy_sites", "prophets", "miracles", "worship")


@dataclass
class Sources:
    temples: int = 0
    holy_sites: int = 0
    prophets: int = 0
    miracles: int = 0
    worship: int = 0

    def total(self) -> int:
        return self.temples + self.holy_sites + self.prophets + self.miracles + self.worship


@dataclass
class DominionTally:
    regions: int = 0
    rows: int = 0
    contested: int = 0
    turned: int = 0
    modifiers: int = 0
    thoughts: int = 0
    drifted: int = 0


@dataclass(frozen=True)
class Want:
    target: int
    key: str
    op: ModifierOp
    god: int
    reason: str


@dataclass
class Gathered:
    sources: dict[tuple[int, int], Sources] = field(default_factory=lambda: defaultdict(Sources))
    patrons: dict[int, int] = field(default_factory=dict)


async def patrons(ctx: TickContext) -> dict[int, int]:
    found: dict[int, int] = {}
    statement = (
        select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
    )
    for source, target in await ctx.session.execute(statement):
        found.setdefault(int(source), int(target))
    return found


async def gather(ctx: TickContext, atlas: RegionAtlas) -> Gathered:
    table = ctx.rules.dominion
    gathered = Gathered(patrons=await patrons(ctx))
    temples = await ctx.session.execute(
        select(EntityRow, StructureProfileRow)
        .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
        .where(StructureProfileRow.kind == StructureKind.TEMPLE, StructureProfileRow.dedicated_son_id.is_not(None), EntityRow.status == EntityStatus.CANON)
    )
    for temple, profile in temples:
        region = atlas.top_region(temple.id)
        if region is not None and profile.dedicated_son_id is not None:
            weight = table.temple_weight * stat_or(temple, "splendor", PERCENT // 2) / PERCENT * profile.staff_pct / PERCENT
            gathered.sources[(profile.dedicated_son_id, region)].temples += round_half_up(weight)
    holdings = await ctx.session.execute(
        select(PlaceProfileRow.entity_id, PlaceProfileRow.sacredness, CultHoldingRow.cult_entity_id)
        .join(CultHoldingRow, CultHoldingRow.holding_entity_id == PlaceProfileRow.entity_id)
        .where(PlaceProfileRow.sacredness > 0)
    )
    for place_id, sacredness, cult_id in holdings:
        god = gathered.patrons.get(int(cult_id))
        region = atlas.top_region(int(place_id))
        if god is not None and region is not None:
            gathered.sources[(god, region)].holy_sites += round_half_up(table.holy_site_weight * sacredness / PERCENT)
    for throne in await ctx.session.scalars(select(ThroneRow).where(ThroneRow.holder_node_id.is_not(None))):
        region = atlas.top_region(throne.place_entity_id)
        if region is not None and throne.holder_node_id is not None:
            gathered.sources[(throne.holder_node_id, region)].holy_sites += round_half_up(table.throne_weight * throne.power / PERCENT)
    flagged = select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.PROPHET)
    prophets = await ctx.session.scalars(
        select(EntityRow).where(
            EntityRow.status == EntityStatus.CANON,
            EntityRow.entity_type == EntityType.MORTAL,
            (EntityRow.id.in_(flagged)) | (EntityRow.mortal_role == MortalRole.SAINT),
        )
    )
    for prophet in prophets:
        god = gathered.patrons.get(prophet.id)
        region = atlas.top_region(prophet.id)
        if god is not None and region is not None:
            gathered.sources[(god, region)].prophets += table.prophet_weight
    for miracle in await ctx.session.scalars(select(MiracleRecordRow).where(MiracleRecordRow.epoch == ctx.epoch)):
        god = miracle.credited_node_id or miracle.god_node_id
        if miracle.region_entity_id is not None:
            gathered.sources[(god, miracle.region_entity_id)].miracles += round_half_up(miracle.belief * table.miracle_weight_pct / PERCENT)
    for community in await canon(ctx.session, list(COMMUNITY_TYPES)):
        god = gathered.patrons.get(community.id)
        region = atlas.top_region(community.id)
        if god is not None and region is not None:
            folk = stat_or(community, "population", table.worship_population)
            gathered.sources[(god, region)].worship += round_half_up(table.worship_weight * min(1.0, folk / table.worship_population))
    return gathered


def spread_from(ctx: TickContext, atlas: RegionAtlas, strengths: dict[tuple[int, int], int], thrones: dict[int, int]) -> dict[tuple[int, int], int]:
    table = ctx.rules.dominion
    reached: dict[tuple[int, int], int] = {}
    for (god, region), value in strengths.items():
        boost = PERCENT + thrones.get(god, 0) * ctx.rules.thrones.spread_pct
        carried = round_half_up(value * table.spread_pct / PERCENT * boost / PERCENT)
        if carried <= 0:
            continue
        for neighbour in atlas.neighbour_regions(region):
            reached[(god, neighbour)] = max(reached.get((god, neighbour), 0), carried)
    return reached


def contest(ctx: TickContext, strengths: dict[tuple[int, int], int], tally: DominionTally) -> None:
    by_region: dict[int, list[int]] = defaultdict(list)
    for god, region in strengths:
        by_region[region].append(god)
    for region, gods in by_region.items():
        present = [god for god in gods if strengths[(god, region)] > 0]
        if len(present) < 2:
            continue
        tally.contested += 1
        strongest = max(present, key=lambda god: (strengths[(god, region)], -god))
        for rival in present:
            if rival == strongest:
                continue
            taken = round_half_up(strengths[(rival, region)] * ctx.rules.dominion.contest_pct / PERCENT)
            strengths[(rival, region)] -= taken
            strengths[(strongest, region)] = min(PERCENT, strengths[(strongest, region)] + taken)


async def settle(ctx: TickContext, atlas: RegionAtlas, gathered: Gathered, tally: DominionTally) -> None:
    table = ctx.rules.dominion
    rows = {(row.god_node_id, row.region_entity_id): row for row in await ctx.session.scalars(select(DominionRow))}
    designs = (await DominionBook.load(ctx.session)).designs
    strengths: dict[tuple[int, int], int] = {}
    for key, found in gathered.sources.items():
        design = designs.get(key[0])
        bonus = round_half_up(design.dominion_strength * table.strength_weight_pct / PERCENT) if design is not None and found.total() > 0 else 0
        strengths[key] = clamp_int(found.total() + bonus, 0, PERCENT)
    for key, row in rows.items():
        decayed = round_half_up(row.strength * (PERCENT - table.decay_pct) / PERCENT)
        strengths[key] = max(strengths.get(key, 0), decayed)
    thrones: dict[int, int] = defaultdict(int)
    for holder in await ctx.session.scalars(select(ThroneRow.holder_node_id).where(ThroneRow.holder_node_id.is_not(None))):
        if holder is not None:
            thrones[holder] += 1
    for key, carried in spread_from(ctx, atlas, strengths, thrones).items():
        strengths[key] = max(strengths.get(key, 0), carried)
    contest(ctx, strengths, tally)
    for key, value in strengths.items():
        god, region = key
        current = rows.get(key)
        if held(god) or held(region) or (current is not None and "strength" in current.locked):
            continue
        found = gathered.sources.get(key, Sources())
        if current is None:
            if value <= 0:
                continue
            current = DominionRow(god_node_id=god, region_entity_id=region, locked=[])
            ctx.session.add(current)
            rows[key] = current
        elif value <= 0 and found.total() == 0:
            await ctx.session.delete(current)
            continue
        settled = clamp_int(value, 0, PERCENT)
        current.trend = settled - (current.strength or 0)
        current.strength = settled
        for column in COLUMNS:
            setattr(current, column, getattr(found, column))
        current.spread = max(0, current.strength - clamp_int(found.total(), 0, PERCENT))
        current.epoch = ctx.epoch
        tally.rows += 1
    await ctx.session.flush()


async def rebuild_rulers(ctx: TickContext, atlas: RegionAtlas, tally: DominionTally) -> None:
    previous = {row.region_entity_id: row.god_node_id for row in await ctx.session.scalars(select(RegionDominionRow))}
    totals: dict[int, dict[int, int]] = defaultdict(dict)
    for row in await ctx.session.scalars(select(DominionRow).where(DominionRow.strength > 0)):
        totals[row.region_entity_id][row.god_node_id] = row.strength
    open_regions = [region for region in previous if not held(region)]
    if open_regions:
        await ctx.session.execute(delete(RegionDominionRow).where(RegionDominionRow.region_entity_id.in_(open_regions)))
    for region, gods in sorted(totals.items())[: ctx.rules.dominion.regions_max]:
        top = max(gods, key=lambda god: (gods[god], -god))
        if held(region) or held(top):
            continue
        share = round(gods[top] * PERCENT / sum(gods.values()))
        ctx.session.add(
            RegionDominionRow(region_entity_id=region, world_id=atlas.world_of(region), god_node_id=top, share=share, rivals=len(gods) - 1, epoch=ctx.epoch)
        )
        tally.regions += 1
        if previous.get(region) != top and share >= ctx.rules.dominion.dominate_share:
            tally.turned += 1
            god = await ctx.session.get(NodeRow, top)
            place = await ctx.session.get(EntityRow, region)
            if god is not None and place is not None:
                await record(ctx, "dominion.ruled", roles={IncidentRole.SUBJECT: [god.id, place.id, top, region]})
    await ctx.session.flush()


async def wanted(ctx: TickContext, atlas: RegionAtlas, book: DominionBook) -> dict[Want, float]:
    table = ctx.rules.dominion
    found: dict[Want, float] = {}
    communities: dict[int, list[EntityRow]] = defaultdict(list)
    for community in await canon(ctx.session, [EntityType.SETTLEMENT, EntityType.PEOPLE]):
        region = atlas.top_region(community.id)
        if region is not None:
            communities[region].append(community)
    for region in sorted(book.rulers):
        god = book.ruler(ctx.rules, region)
        if god is None or held(region):
            continue
        order, productivity = book.scale_at(ctx.rules, region, DivineScale.ORDER), book.scale_at(ctx.rules, region, DivineScale.PRODUCTIVITY)
        growth, magic = book.scale_at(ctx.rules, region, DivineScale.GROWTH), book.scale_at(ctx.rules, region, DivineScale.MAGIC)
        if order:
            found[Want(region, "danger", ModifierOp.ADD, god, f"{PREFIX}order")] = float(-order * table.danger_per_step)
        if growth:
            found[Want(region, "fertility", ModifierOp.ADD, god, f"{PREFIX}growth")] = float(growth * table.fertility_per_step)
        if magic:
            found[Want(region, "magic", ModifierOp.ADD, god, f"{PREFIX}magic")] = float(magic * table.magic_per_step)
        for community in communities.get(region, []):
            if held(community.id):
                continue
            if order + productivity and community.entity_type is EntityType.SETTLEMENT:
                found[Want(community.id, "prosperity", ModifierOp.ADD, god, f"{PREFIX}prosperity")] = float((order + productivity) * table.prosperity_per_step)
            if growth:
                found[Want(community.id, GROWTH_KEY, ModifierOp.MULTIPLY, god, f"{PREFIX}growth")] = 1 + growth * table.growth_per_step_pct / PERCENT
    return found


async def apply_scales(ctx: TickContext, atlas: RegionAtlas, tally: DominionTally) -> None:
    desired = await wanted(ctx, atlas, await DominionBook.load(ctx.session))
    existing = list(await ctx.session.scalars(select(ModifierRow).where(ModifierRow.reason_key.like(f"{PREFIX}%")).order_by(ModifierRow.id)))
    kept: set[Want] = set()
    stale: list[int] = []
    for row in existing:
        key = Want(row.target_node_id, row.target_key, row.op, row.source_node_id or 0, row.reason_key)
        if held(row.target_node_id) or row.held:
            kept.add(key)
        elif key in desired and key not in kept:
            row.magnitude = desired[key]
            kept.add(key)
        else:
            stale.append(row.id)
    if stale:
        await ctx.session.execute(delete(ModifierRow).where(ModifierRow.id.in_(stale)))
    for want, magnitude in desired.items():
        if want in kept:
            continue
        await add_modifier(
            ctx.session,
            ModifierDraft(
                target_node_id=want.target,
                target_key=want.key,
                op=want.op,
                magnitude=magnitude,
                source_kind=ModifierSource.DOMINION,
                source_node_id=want.god,
                reason_key=want.reason,
                start_epoch=ctx.epoch,
                stacking_group=f"{want.reason}.{want.god}",
            ),
        )
        tally.modifiers += 1
    await ctx.session.flush()


async def presence(ctx: TickContext, atlas: RegionAtlas, gathered: Gathered, tally: DominionTally) -> None:
    table = ctx.rules.dominion
    book = await DominionBook.load(ctx.session)
    for mortal in await canon(ctx.session, [EntityType.MORTAL]):
        if tally.thoughts >= table.thoughts_max:
            break
        if held(mortal.id):
            continue
        ruler = book.ruler(ctx.rules, atlas.top_region(mortal.id))
        patron = gathered.patrons.get(mortal.id)
        if ruler is None or patron is None:
            continue
        if patron == ruler:
            await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.FELT_GOD_NEAR, ctx.epoch, subject_id=ruler)
            await add_stress(ctx.session, mortal.id, -table.near_stress, ctx.epoch)
            tally.thoughts += 1
        elif mortal.mortal_role in CLERGY:
            await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.ALIEN_DOMINION, ctx.epoch, subject_id=ruler)
            await add_stress(ctx.session, mortal.id, table.alien_stress, ctx.epoch)
            tally.thoughts += 1


DEED_SCALES = MappingProxyType(
    {"healing": (DivineScale.GROWTH, 1), "bounty": (DivineScale.PRODUCTIVITY, 1), "peace": (DivineScale.ORDER, 1), "protection": (DivineScale.FORTUNE, 1)}
)


async def drift_scales(ctx: TickContext, tally: DominionTally) -> None:
    table = ctx.rules.dominion
    since = ctx.epoch - ctx.rules.miracle_impression.repeat_window
    counts: dict[tuple[int, DivineScale, int], int] = defaultdict(int)
    for miracle in await ctx.session.scalars(select(MiracleRecordRow).where(MiracleRecordRow.epoch >= since)):
        if miracle.kind in DEED_SCALES:
            scale, step = DEED_SCALES[miracle.kind]
            counts[(miracle.credited_node_id or miracle.god_node_id, scale, step)] += 1
    struck = await ctx.session.scalars(select(ActionRecordRow).where(ActionRecordRow.epoch >= since, ActionRecordRow.kind == ActionKind.DISASTER))
    for act in struck:
        if act.actor_node_id is not None:
            counts[(act.actor_node_id, DivineScale.FORTUNE, -1)] += 1
    for (god, scale, step), count in sorted(counts.items()):
        if count < table.deed_shift_count or held(god):
            continue
        row = await ctx.session.get(GodScaleRow, (god, scale))
        if row is None:
            row = GodScaleRow(god_node_id=god, scale=scale, value=0, locked=[])
            ctx.session.add(row)
        if "value" not in row.locked and SCALE_MIN <= row.value + step <= SCALE_MAX:
            row.value += step
            tally.drifted += 1
    await ctx.session.flush()


async def weigh_dominion(ctx: TickContext, tally: DominionTally) -> None:
    await ensure_designs(ctx.session, ctx.rules, ctx.epoch)
    await drift_scales(ctx, tally)
    atlas = await RegionAtlas.load(ctx.session)
    gathered = await gather(ctx, atlas)
    await settle(ctx, atlas, gathered, tally)
    await rebuild_rulers(ctx, atlas, tally)
    await apply_scales(ctx, atlas, tally)
    await presence(ctx, atlas, gathered, tally)
