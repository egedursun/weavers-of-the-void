from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmography import DimensionRow, RiftRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.made import MadeRealmRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.rift_control import RiftControlRow
from aerona.db.tables.routes import JourneyRow
from aerona.db.write_guard import held
from aerona.domain.enums.cosmography import OPEN_RIFT_STATES, RiftCause, RiftWork
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.travel import JourneyStatus
from aerona.engine.context import TickContext
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.cosmos.rifts import open_rift, rift_cycles
from aerona.engine.economy.purse import give_coin, take_coin
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import change_relation

LARGE = 50


async def control_of(ctx: TickContext, rift: RiftRow) -> RiftControlRow:
    row = await ctx.session.get(RiftControlRow, rift.id)
    if row is None:
        row = RiftControlRow(rift_id=rift.id, locked=[])
        ctx.session.add(row)
    return row


async def claimant_for(ctx: TickContext, rift: RiftRow) -> int | None:
    if rift.region_entity_id is None:
        return None
    towns = select(EntityRow.id).where(EntityRow.location_id == rift.region_entity_id, EntityRow.entity_type == EntityType.SETTLEMENT)
    return await ctx.session.scalar(
        select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id.in_(towns)).order_by(PolityMemberRow.polity_entity_id).limit(1)
    )


def chosen_work(rift: RiftRow) -> RiftWork:
    if rift.route_id is not None:
        return RiftWork.GATE
    return RiftWork.SEALING if rift.size >= LARGE else RiftWork.STABILISING


async def work_on(ctx: TickContext, rift: RiftRow, row: RiftControlRow) -> None:
    table = ctx.rules.rift_control
    if row.work is RiftWork.SEALING and "size" not in rift.locked:
        rift.size = clamp_percent(rift.size - table.seal_step)
    elif row.work is RiftWork.STABILISING and "stability" not in rift.locked:
        rift.stability = clamp_percent(rift.stability + table.stabilise_step)
    elif row.work is RiftWork.GATE and row.claimant_entity_id is not None and rift.route_id is not None:
        await collect_tolls(ctx, rift.route_id, row.claimant_entity_id, row.toll or table.gate_toll)


async def collect_tolls(ctx: TickContext, route_id: int, keeper_id: int, toll: int) -> int:
    keeper = await ctx.session.get(EntityRow, keeper_id)
    if keeper is None or held(keeper.id):
        return 0
    paid = 0
    crossing = select(JourneyRow.traveller_entity_id).where(JourneyRow.route_id == route_id, JourneyRow.status == JourneyStatus.UNDERWAY)
    for traveller_id in sorted(set(await ctx.session.scalars(crossing))):
        traveller = await ctx.session.get(EntityRow, traveller_id)
        if traveller is None or traveller.id == keeper.id or held(traveller.id):
            continue
        if await take_coin(ctx.session, ctx.rules, traveller, toll):
            await give_coin(ctx.session, ctx.rules, keeper, toll)
            paid += toll
    return paid


async def adapt(ctx: TickContext, rift: RiftRow, row: RiftControlRow) -> None:
    table = ctx.rules.rift_control
    if "adapted" not in row.locked:
        row.adapted = clamp_percent(row.adapted + table.adapt_step)
    region = await ctx.session.get(EntityRow, rift.region_entity_id) if rift.region_entity_id is not None else None
    if region is not None and row.adapted >= table.adapted_at and not held(region.id):
        shift_stat(region, "fertility", table.adapted_fertility, low=0, high=PERCENT)


async def keep_claims(ctx: TickContext, rift: RiftRow, row: RiftControlRow) -> None:
    if "claimant_entity_id" in row.locked or rift.opened_epoch > ctx.epoch - ctx.rules.rift_control.claim_epochs:
        return
    claimant = await claimant_for(ctx, rift)
    if claimant is not None and claimant != row.claimant_entity_id and not held(claimant):
        row.claimant_entity_id, row.claimed_epoch = claimant, ctx.epoch
        where = rift.region_entity_id or rift.world_id
        await record(ctx, "rift.claimed", roles={IncidentRole.ACTOR: claimant, IncidentRole.PLACE: where}, place=where, world_id=rift.world_id)
    if row.claimant_entity_id is not None and "work" not in row.locked and row.work is RiftWork.NONE:
        row.work = chosen_work(rift)


async def rival_claims(ctx: TickContext) -> int:
    claims: dict[int, set[int]] = {}
    for world_id, claimant in await ctx.session.execute(
        select(RiftRow.world_id, RiftControlRow.claimant_entity_id)
        .join(RiftRow, RiftRow.id == RiftControlRow.rift_id)
        .where(RiftControlRow.claimant_entity_id.is_not(None))
    ):
        if claimant is not None:
            claims.setdefault(world_id, set()).add(claimant)
    strained = 0
    for claimants in claims.values():
        ordered = sorted(claimants)
        for index, first in enumerate(ordered):
            for second in ordered[index + 1 :]:
                if not held(first, second):
                    await change_relation(ctx, first, second, -ctx.rules.rift_control.claim_tension, MemoryKind.ILL_WILL, note="rival claims on rifts")
                    strained += 1
    return strained


async def realm_gates(ctx: TickContext) -> int:
    opened = 0
    gated = set(
        await ctx.session.scalars(select(RiftRow.dimension_id).where(RiftRow.cause == RiftCause.MADE_REALM_GATE, RiftRow.state.in_(list(OPEN_RIFT_STATES))))
    )
    for realm in list(await ctx.session.scalars(select(MadeRealmRow).where(MadeRealmRow.host_node_id.is_not(None), MadeRealmRow.sealed.is_(False)))):
        if realm.dimension_id in gated or realm.host_node_id is None:
            continue
        host = await ctx.session.get(EntityRow, realm.host_node_id)
        dimension = await ctx.session.get(DimensionRow, realm.dimension_id)
        world = await ctx.session.get(WorldRow, host.world_id) if host is not None else None
        region = await ctx.session.get(EntityRow, host.location_id) if host is not None and host.location_id is not None else None
        if host is None or dimension is None or world is None or held(host.id, world.id):
            continue
        if (await Cosmography.load(ctx.session)).place_world(world).dimension_id == dimension.id:
            continue
        place = region if region is not None and region.entity_type is EntityType.REGION else None
        await open_rift(ctx, world, place, dimension, RiftCause.MADE_REALM_GATE, by_node_id=host.id)
        opened += 1
    return opened


async def keep_rift_control(ctx: TickContext) -> None:
    for rift in list(await ctx.session.scalars(select(RiftRow).where(RiftRow.state.in_(list(OPEN_RIFT_STATES))).order_by(RiftRow.id))):
        if held(rift.world_id, rift.region_entity_id, rift.dimension_id):
            continue
        row = await control_of(ctx, rift)
        await keep_claims(ctx, rift, row)
        await work_on(ctx, rift, row)
        await adapt(ctx, rift, row)
    ctx.count("rift_rivalries", await rival_claims(ctx))
    ctx.count("realm_gates", await realm_gates(ctx))


@reads(
    "table.community_relations",
    "table.cosmos",
    "table.dimensional_events",
    "table.dimensions",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.journeys",
    "table.made_realm_profiles",
    "table.made_realms",
    "table.nodes",
    "table.phenomenon_footprints",
    "table.phenomenon_profiles",
    "table.polity_members",
    "table.region_environment",
    "table.rift_controls",
    "table.rifts",
    "table.stars",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.region_environment",
    "table.rift_controls",
    "table.rifts",
    "table.routes",
)
async def rifts_and_control(ctx: TickContext) -> None:
    await rift_cycles(ctx)
    await keep_rift_control(ctx)
