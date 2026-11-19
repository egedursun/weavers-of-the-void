from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.works_shapes import WORKS_PROSPERITY_PCT
from aerona.constants.units import PERCENT
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.works import PublicWorksRow, PublicWorkStageRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.settlement import WATER_ORDER
from aerona.domain.enums.works import LabourRegime, WorksKind, WorksStatus
from aerona.engine.context import TickContext
from aerona.engine.numbers.book import towns_in
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining, term

LEVEL_MAX = 5
WORKS_LEVELS: dict[WorksKind, tuple[str, int, int | None]] = {
    WorksKind.ROAD: ("roads", 1, LEVEL_MAX),
    WorksKind.RAIL_LINE: ("roads", 1, LEVEL_MAX),
    WorksKind.BRIDGE: ("bridges", 1, LEVEL_MAX),
    WorksKind.DAM: ("irrigation", 1, LEVEL_MAX),
    WorksKind.DRAINAGE: ("irrigation", 1, LEVEL_MAX),
    WorksKind.WALLS: ("walls_level", 1, LEVEL_MAX),
    WorksKind.CANAL: ("harbour_capacity", 10, None),
    WorksKind.HARBOUR_WORKS: ("harbour_capacity", 20, None),
    WorksKind.GRANARY_SYSTEM: ("granary_capacity", 50, None),
}
ROUTE_WORKS = frozenset({WorksKind.ROAD, WorksKind.RAIL_LINE, WorksKind.BRIDGE, WorksKind.CANAL})
ROUTE_SHORTENING_PCT = 10
SANITATION_GAIN = 10
UNPAID_LABOUR = frozenset({LabourRegime.CORVEE, LabourRegime.BOUND})
MADE_LABOUR = frozenset({LabourRegime.MADE_MINDS, LabourRegime.CONSTRUCTS})


@dataclass
class WorksTally:
    stages: int = 0
    delayed: int = 0
    finished: int = 0
    failed: int = 0
    neglected: int = 0


async def take_treasury(session: AsyncSession, holder_id: int, amount: int) -> bool:
    if amount <= 0:
        return True
    realm = await session.get(PolityProfileRow, holder_id)
    if realm is not None:
        if realm.treasury < amount or "treasury" in (realm.locked or []):
            return False
        realm.treasury -= amount
        return True
    town = await session.get(SettlementProfileRow, holder_id)
    if town is None or town.treasury < amount or "treasury" in (town.locked or []):
        return False
    town.treasury -= amount
    return True


async def towns_of_place(session: AsyncSession, place_id: int) -> list[int]:
    route = await session.get(TradeRouteProfileRow, place_id)
    if route is not None:
        return []
    node = await session.get(EntityRow, place_id)
    if node is None:
        return []
    if node.entity_type in {EntityType.SETTLEMENT, EntityType.PEOPLE, EntityType.POLITY}:
        return await towns_in(session, place_id)
    rows = await session.scalars(
        select(EntityRow.id).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == place_id)
    )
    return sorted(rows)


async def shift_infrastructure(session: AsyncSession, town_id: int, kind: WorksKind, sign: int) -> None:
    row = await session.get(SettlementInfrastructureRow, town_id)
    if row is None or held(town_id):
        return
    if kind is WorksKind.SEWER and "sewers" not in (row.locked or []):
        row.sewers = sign > 0
    elif kind is WorksKind.AQUEDUCT and "water" not in (row.locked or []):
        index = WATER_ORDER.index(row.water) + sign
        row.water = WATER_ORDER[clamp_int(index, 0, len(WATER_ORDER) - 1)]
    elif kind in WORKS_LEVELS:
        column, step, cap = WORKS_LEVELS[kind]
        if column not in (row.locked or []):
            value = max(0, getattr(row, column) + sign * step)
            setattr(row, column, min(value, cap) if cap is not None else value)


async def apply_works(ctx: TickContext, works: PublicWorksRow, sign: int) -> None:
    route = await ctx.session.get(TradeRouteProfileRow, works.place_node_id)
    if route is not None and works.kind in ROUTE_WORKS and not held(works.place_node_id) and "length" not in (route.locked or []):
        change = max(1, round_half_up(route.length * ROUTE_SHORTENING_PCT / PERCENT))
        route.length = max(1, route.length - sign * change)
    for town_id in await towns_of_place(ctx.session, works.place_node_id):
        if works.kind in WORKS_LEVELS or works.kind in {WorksKind.SEWER, WorksKind.AQUEDUCT}:
            await shift_infrastructure(ctx.session, town_id, works.kind, sign)
            if works.kind in {WorksKind.SEWER, WorksKind.AQUEDUCT}:
                profile = await ctx.session.get(SettlementProfileRow, town_id)
                if profile is not None and not held(town_id) and "sanitation" not in (profile.locked or []):
                    profile.sanitation = clamp_int(profile.sanitation + sign * SANITATION_GAIN, 0, PERCENT)
            continue
        town = await ctx.session.get(EntityRow, town_id)
        if town is not None and not held(town_id):
            gain = sign * ctx.rules.public_works.finished_prosperity * WORKS_PROSPERITY_PCT.get(works.kind, PERCENT) / PERCENT
            with explaining():
                term("public_works.finished_prosperity", gain, source_node_id=works.polity_entity_id)
                shift_stat(town, "prosperity", gain, low=0, high=PERCENT)


async def grieve(ctx: TickContext, works: PublicWorksRow) -> None:
    amount = ctx.rules.public_works.labour_grievance
    for town_id in await towns_in(ctx.session, works.polity_entity_id):
        profile = await ctx.session.get(SettlementProfileRow, town_id)
        if profile is not None and not held(town_id) and "unrest" not in (profile.locked or []):
            with explaining():
                term("public_works.labour_grievance", amount, source_node_id=works.polity_entity_id)
                profile.unrest = clamp_int(profile.unrest + amount, 0, PERCENT)


async def fail(ctx: TickContext, works: PublicWorksRow, cause: str, tally: WorksTally) -> None:
    if works.status is WorksStatus.FINISHED:
        await apply_works(ctx, works, -1)
    works.status = WorksStatus.FAILED
    await record(
        ctx,
        "works.failed",
        roles={IncidentRole.ACTOR: works.polity_entity_id, IncidentRole.PLACE: works.place_node_id},
        facts={"kind": works.kind, "cause": cause},
    )
    tally.failed += 1


async def pay_labour(ctx: TickContext, works: PublicWorksRow) -> int | None:
    cost = ctx.rules.public_works.labour_per_stage
    if works.labour in UNPAID_LABOUR:
        await grieve(ctx, works)
        return 0
    if works.labour in MADE_LABOUR:
        cost //= 2
    from_budget = min(works.budget, cost)
    if not await take_treasury(ctx.session, works.polity_entity_id, cost - from_budget):
        return None
    if "budget" not in (works.locked or []):
        works.budget -= from_budget
    return cost


async def finish_stage(ctx: TickContext, works: PublicWorksRow, spent: int) -> bool:
    roles = {IncidentRole.ACTOR: works.polity_entity_id, IncidentRole.PLACE: works.place_node_id}
    works.stage, works.progress = works.stage + 1, 0
    ctx.session.add(
        PublicWorkStageRow(
            works_id=works.id,
            polity_entity_id=works.polity_entity_id,
            stage=works.stage,
            labour=works.labour,
            spent=spent,
            quality=works.quality,
            done_epoch=ctx.epoch,
            locked=[],
        )
    )
    await record(ctx, "works.stage_done", roles=roles, facts={"kind": works.kind, "stage": works.stage, "stages": works.stages})
    if works.stage < works.stages:
        return False
    works.status, works.finished_epoch = WorksStatus.FINISHED, ctx.epoch
    await apply_works(ctx, works, 1)
    await record(ctx, "works.finished", roles=roles, facts={"kind": works.kind, "quality": works.quality})
    return True


async def advance(ctx: TickContext, works: PublicWorksRow, tally: WorksTally) -> None:
    table = ctx.rules.public_works
    spent = None if "stage" in (works.locked or []) else await pay_labour(ctx, works)
    if spent is None:
        roles = {IncidentRole.ACTOR: works.polity_entity_id, IncidentRole.PLACE: works.place_node_id}
        await record(ctx, "works.delayed", roles=roles, facts={"kind": works.kind, "stage": works.stage})
        tally.delayed += 1
        return
    if works.quality < table.quality_floor and ctx.rng(f"works_collapse.{works.id}.{ctx.epoch}").chance(table.collapse_pct):
        await fail(ctx, works, "a stage collapsed", tally)
        return
    tally.stages += 1
    if await finish_stage(ctx, works, spent):
        tally.finished += 1


async def keep_up(ctx: TickContext, works: PublicWorksRow, tally: WorksTally) -> None:
    table = ctx.rules.public_works
    owed = round_half_up(works.budget * table.upkeep_pct / PERCENT)
    if owed and not await take_treasury(ctx.session, works.polity_entity_id, owed) and "condition" not in (works.locked or []):
        works.condition = clamp_int(works.condition - table.decay_per_neglected_epoch, 0, PERCENT)
        await record(
            ctx,
            "works.neglected",
            roles={IncidentRole.ACTOR: works.polity_entity_id, IncidentRole.PLACE: works.place_node_id},
            facts={"kind": works.kind, "condition": works.condition},
        )
        tally.neglected += 1
    if works.condition <= 0:
        await fail(ctx, works, "it fell into ruin", tally)
    elif works.quality < table.quality_floor and ctx.rng(f"works_flood.{works.id}.{ctx.epoch}").chance(table.collapse_pct / 2):
        await fail(ctx, works, "it gave way", tally)


async def keep_works(ctx: TickContext) -> WorksTally:
    tally = WorksTally()
    for works in list(await ctx.session.scalars(select(PublicWorksRow).where(PublicWorksRow.status != WorksStatus.FAILED).order_by(PublicWorksRow.id))):
        if held(works.polity_entity_id) or held(works.place_node_id) or "status" in (works.locked or []):
            continue
        if works.status is WorksStatus.BUILDING:
            await advance(ctx, works, tally)
        else:
            await keep_up(ctx, works, tally)
    await ctx.session.flush()
    return tally
