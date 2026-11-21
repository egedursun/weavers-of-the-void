from sqlalchemy import select

from aerona.catalog.civilization import unlocked
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interworld import InterworldMigrationRow
from aerona.db.tables.military import OccupationRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.civilization import TierCapability
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.interworld import MigrationCause, MigrationReception
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.travel import JourneyIntent, JourneyStatus
from aerona.engine.context import TickContext
from aerona.engine.cosmos.routes import can_use_route
from aerona.engine.interworld.book import InterworldTally, route_between, route_open
from aerona.engine.phases.travel import send_expedition
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.record import record
from aerona.engine.services.war import current_war

MC = MigrationCause
CAUSE_WEIGHT = total(
    MigrationCause,
    {MC.FLIGHT: 100, MC.LAND_HUNGER: 60, MC.FAITH_CALL: 50, MC.EXILE: 80, MC.LABOUR_DRAW: 50, MC.WORLD_DYING: 120, MC.RESETTLEMENT: 100},
)
MR = MigrationReception
RECEPTION_SHARE = total(MigrationReception, {MR.WELCOME: 100, MR.QUOTA: 50, MR.REFUSAL: 0})
CROWDED = 20
PEOPLE_PER_PROSPERITY = 200


async def blocked(ctx: TickContext, community: EntityRow, route: RouteRow) -> str | None:
    if not unlocked(ctx.rules, community.civ_tier or 0, TierCapability.COLONY):
        return "it has not grown enough as a civilization to cross between worlds"
    return await can_use_route(ctx.session, ctx.rules, ctx.epoch, community, route)


async def reception_at(ctx: TickContext, community: EntityRow, to_world: int) -> MigrationReception:
    homes = set(await ctx.session.scalars(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == community.id)))
    hosts = select(EntityRow.id).where(EntityRow.world_id == to_world, EntityRow.entity_type == EntityType.POLITY, EntityRow.status == EntityStatus.CANON)
    for host in await ctx.session.scalars(hosts.order_by(EntityRow.id)):
        if any([await current_war(ctx.session, host, home) is not None for home in sorted(homes | {community.id})]):
            return MigrationReception.REFUSAL
    there = select(EntityRow).where(EntityRow.world_id == to_world, EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
    crowd = sum(stat(town, "population") or 0 for town in await ctx.session.scalars(there))
    return MigrationReception.QUOTA if crowd > (stat(community, "population") or 0) * CROWDED else MigrationReception.WELCOME


async def begin(
    ctx: TickContext, community: EntityRow, to_world: int, cause: MigrationCause, route: RouteRow, *, tally: InterworldTally
) -> InterworldMigrationRow:
    query = select(InterworldMigrationRow).where(InterworldMigrationRow.community_entity_id == community.id, InterworldMigrationRow.ended_epoch.is_(None))
    found = await ctx.session.scalar(query.limit(1))
    if found is not None:
        return found
    share = ctx.rules.interworld.migration_share_pct * CAUSE_WEIGHT[cause] // PERCENT
    row = InterworldMigrationRow(
        community_entity_id=community.id,
        from_world_id=community.world_id or to_world,
        to_world_id=to_world,
        route_id=route.id,
        cause=cause,
        reception=await reception_at(ctx, community, to_world),
        per_epoch=max(1, round_half_up((stat(community, "population") or 0) * share / PERCENT)),
        begun_epoch=ctx.epoch,
        journey_ids=[],
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    tally.migrations += 1
    await record(
        ctx,
        "migration.interworld_began",
        roles={IncidentRole.SUBJECT: community.id},
        facts={"cause": cause, "per_epoch": row.per_epoch, "reception": row.reception},
        world_id=to_world,
    )
    return row


async def move(ctx: TickContext, row: InterworldMigrationRow, community: EntityRow, tally: InterworldTally) -> None:
    table = ctx.rules.interworld
    route = await ctx.session.get(RouteRow, row.route_id) if row.route_id is not None else None
    if route is None or not await route_open(ctx, route) or await blocked(ctx, community, route) is not None:
        return
    allowed = row.per_epoch * RECEPTION_SHARE[row.reception] // PERCENT
    if not allowed:
        row.waiting += row.per_epoch
        tally.refused += 1
        await record(ctx, "migration.interworld_refused", roles={IncidentRole.SUBJECT: community.id}, facts={"waiting": row.waiting}, world_id=row.to_world_id)
        return
    moved = min(allowed, route.capacity * table.carrier_people_per_capacity, stat(community, "population") or 0)
    if moved <= 0:
        return
    journey = await send_expedition(ctx.session, ctx.rules, community.id, route.id, JourneyIntent.COLONY, population=moved)
    row.journey_ids = [*(row.journey_ids or []), journey.id]
    row.moved += moved
    tally.migrants += moved


async def count_arrivals(ctx: TickContext, row: InterworldMigrationRow, tally: InterworldTally) -> None:
    counted = 0
    pending: list[int] = []
    for journey_id in row.journey_ids or []:
        journey = await ctx.session.get(JourneyRow, journey_id)
        if journey is not None and journey.status is JourneyStatus.ARRIVED:
            counted += journey.population
        elif journey is not None and journey.status is JourneyStatus.UNDERWAY:
            pending.append(journey_id)
    if counted:
        row.arrived += counted
        tally.arrived += counted
        await record(
            ctx, "migration.interworld_arrived", roles={IncidentRole.SUBJECT: row.community_entity_id}, facts={"arrived": counted}, world_id=row.to_world_id
        )
    row.journey_ids = pending


async def push_of(ctx: TickContext, atlas: RegionAtlas, town: EntityRow) -> tuple[int, MigrationCause]:
    region = atlas.top_region(town.id)
    profile = await ctx.session.get(SettlementProfileRow, town.id)
    unrest = profile.unrest if profile is not None else 0
    if region is not None and await ctx.session.get(OccupationRow, region) is not None:
        return clamp_int(unrest + PERCENT // 2, 0, PERCENT), MigrationCause.FLIGHT
    room = max(1, (stat(town, "prosperity") or 0) * PEOPLE_PER_PROSPERITY)
    crowding = clamp_int((stat(town, "population") or 0) * PERCENT // room, 0, PERCENT)
    return max(crowding, unrest), MigrationCause.LAND_HUNGER


async def migrations_to_begin(ctx: TickContext, tally: InterworldTally) -> None:
    table = ctx.rules.interworld
    routes = list(await ctx.session.scalars(select(RouteRow).where(RouteRow.active.is_(True)).order_by(RouteRow.id)))
    worlds = sorted({world for route in routes for world in (route.world_a_id, route.world_b_id)})
    if not worlds:
        return
    atlas = await RegionAtlas.load(ctx.session)
    query = select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.world_id.in_(worlds))
    for town in list(await ctx.session.scalars(query.order_by(EntityRow.id))):
        if held(town.id) or town.world_id is None:
            continue
        push, cause = await push_of(ctx, atlas, town)
        if push < table.migration_push_threshold or not ctx.rng(f"migration.{town.id}.{ctx.epoch}").chance(table.migration_chance_pct):
            continue
        others = [world for world in worlds if world != town.world_id]
        target = ctx.rng(f"migration.to.{town.id}.{ctx.epoch}").pick_or_none(others)
        route = await route_between(ctx, town.world_id, target) if target is not None else None
        if route is not None and target is not None and await blocked(ctx, town, route) is None:
            await begin(ctx, town, target, cause, route, tally=tally)


async def tend_migrations(ctx: TickContext, tally: InterworldTally) -> None:
    cap = ctx.rules.interworld.migration_cap_pct
    for row in list(
        await ctx.session.scalars(select(InterworldMigrationRow).where(InterworldMigrationRow.ended_epoch.is_(None)).order_by(InterworldMigrationRow.id))
    ):
        community = await ctx.session.get(EntityRow, row.community_entity_id)
        if community is None or held(community.id):
            continue
        await count_arrivals(ctx, row, tally)
        if community.status is not EntityStatus.CANON or row.moved * PERCENT >= (row.moved + (stat(community, "population") or 0)) * cap:
            row.ended_epoch = ctx.epoch
            continue
        await move(ctx, row, community, tally)
    await migrations_to_begin(ctx, tally)
