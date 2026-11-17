from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.integrity import MegastructureRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.structure import STANDING_STATES, StructureKind
from aerona.engine.context import TickContext
from aerona.engine.cosmos.orbits import planet_of
from aerona.engine.economy.purse import give_coin
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record
from aerona.engine.renown.currencies import realm_of_community
from aerona.engine.services.community_relations import change_relation
from aerona.engine.structures.integrity import integrity_share

K = StructureKind
ROUTE_DANGERS = ("danger_bandits", "danger_beasts", "danger_weather", "danger_sea")


@dataclass
class MegaTally:
    running: int = 0
    coin: int = 0
    dimmed: int = 0
    routes_eased: int = 0
    moved: int = 0


async def state_of(session: AsyncSession, structure_id: int, epoch: int) -> MegastructureRow:
    row = await session.get(MegastructureRow, structure_id)
    if row is None:
        row = MegastructureRow(structure_entity_id=structure_id, target_orbit=None, output=0, updated_epoch=epoch, locked=[])
        session.add(row)
        await session.flush()
    return row


async def owner_of(session: AsyncSession, profile: StructureProfileRow) -> EntityRow | None:
    if profile.host_entity_id is None:
        return None
    realm = await realm_of_community(session, profile.host_entity_id)
    return await living_entity(session, realm if realm is not None else profile.host_entity_id)


async def host_world(session: AsyncSession, profile: StructureProfileRow) -> WorldRow | None:
    host = await session.get(EntityRow, profile.host_entity_id) if profile.host_entity_id is not None else None
    return await session.get(WorldRow, host.world_id) if host is not None and host.world_id is not None else None


async def collect(ctx: TickContext, profile: StructureProfileRow, strength: float, state: MegastructureRow, tally: MegaTally) -> None:
    table = ctx.rules.megastructures
    owner = await owner_of(ctx.session, profile)
    world = await host_world(ctx.session, profile)
    coin = round_half_up(profile.level * table.collector_coin * strength)
    if owner is not None and coin > 0 and not held(owner.id):
        await give_coin(ctx.session, ctx.rules, owner, coin)
        tally.coin += coin
    if "output" not in state.locked:
        state.output = coin
    star = await ctx.session.get(StarRow, world.star_id) if world is not None and world.star_id is not None else None
    if star is None or held(star.id):
        return
    floor = table.collector_floor
    if star.brightness > floor and "brightness" not in (star.locked or []):
        star.brightness = max(floor, star.brightness - round_half_up(table.collector_dim * strength))
        tally.dimmed += 1
    if owner is None:
        return
    worshippers = await ctx.session.scalars(
        select(BondRow.source_node_id).where(BondRow.target_node_id == star.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    )
    for worshipper in list(worshippers):
        if worshipper != owner.id and not held(worshipper):
            await change_relation(ctx, worshipper, owner.id, -table.collector_regard, MemoryKind.DESECRATED_HOLY, note="dimmed the star they worship")


async def beacon(ctx: TickContext, profile: StructureProfileRow, strength: float, state: MegastructureRow, tally: MegaTally) -> None:
    world = await host_world(ctx.session, profile)
    if world is None:
        return
    relief = round_half_up(ctx.rules.megastructures.beacon_relief * strength)
    eased = 0
    markets = select(EntityRow.id).where(EntityRow.world_id == world.id)
    for route in await ctx.session.scalars(
        select(TradeRouteProfileRow).where(or_(TradeRouteProfileRow.first_market_id.in_(markets), TradeRouteProfileRow.second_market_id.in_(markets)))
    ):
        if held(route.route_entity_id):
            continue
        for column in ROUTE_DANGERS:
            if column not in (route.locked or []):
                setattr(route, column, max(0, getattr(route, column) - relief))
        eased += 1
    eased += await ease_cosmic_routes(ctx, world.id, relief)
    if "output" not in state.locked:
        state.output = eased
    tally.routes_eased += eased


async def ease_cosmic_routes(ctx: TickContext, world_id: int, relief: int) -> int:
    eased = 0
    for route in await ctx.session.scalars(select(RouteRow).where(or_(RouteRow.world_a_id == world_id, RouteRow.world_b_id == world_id))):
        if "danger" not in (route.locked or []):
            route.danger = clamp_int(route.danger - relief, 0, PERCENT)
            eased += 1
    return eased


async def ring(ctx: TickContext, profile: StructureProfileRow, strength: float, state: MegastructureRow, tally: MegaTally) -> None:
    world = await host_world(ctx.session, profile)
    if world is None:
        return
    eased = await ease_cosmic_routes(ctx, world.id, round_half_up(ctx.rules.megastructures.ring_relief * strength))
    if "output" not in state.locked:
        state.output = eased
    tally.routes_eased += eased


async def engine(ctx: TickContext, profile: StructureProfileRow, strength: float, state: MegastructureRow, tally: MegaTally) -> None:
    world = await host_world(ctx.session, profile)
    if world is None or state.target_orbit is None:
        return
    planet = await planet_of(ctx.session, world)
    if held(planet.id) or "orbit" in (planet.locked or []):
        return
    gap = state.target_orbit - planet.orbit
    step = ctx.rules.megastructures.engine_step_pct / PERCENT * strength
    moved = max(-step, min(step, gap))
    if abs(moved) <= 0:
        return
    planet.orbit = max(0.01, planet.orbit + moved)
    if "output" not in state.locked:
        state.output = round_half_up(abs(moved) * PERCENT)
    tally.moved += 1


@memoized(StructureProfileRow)
async def habitat_hosts(session: AsyncSession) -> frozenset[int | None]:
    return frozenset(await session.scalars(select(StructureProfileRow.host_entity_id).where(StructureProfileRow.kind == K.HABITAT_RING)))


async def habitat_room(session: AsyncSession, settlement_id: int) -> int:
    room = 0
    if settlement_id not in await habitat_hosts(session):
        return room
    statement = select(StructureProfileRow).where(StructureProfileRow.host_entity_id == settlement_id, StructureProfileRow.kind == K.HABITAT_RING)
    for profile in await session.scalars(statement):
        if profile.construction_state in STANDING_STATES:
            room += round_half_up(profile.capacity * await integrity_share(session, profile.structure_entity_id))
    return room


async def run_megastructures(ctx: TickContext) -> MegaTally:
    tally = MegaTally()
    kinds = {K.STAR_COLLECTOR: collect, K.BEACON: beacon, K.ORBITAL_RING: ring, K.PLANETARY_ENGINE: engine}
    statement = select(StructureProfileRow).where(StructureProfileRow.kind.in_(list(kinds))).order_by(StructureProfileRow.structure_entity_id)
    for profile in list(await ctx.session.scalars(statement)):
        if profile.construction_state not in STANDING_STATES or held(profile.structure_entity_id):
            continue
        strength = profile.effect_pct / PERCENT * await integrity_share(ctx.session, profile.structure_entity_id)
        if strength <= 0:
            continue
        state = await state_of(ctx.session, profile.structure_entity_id, ctx.epoch)
        await kinds[profile.kind](ctx, profile, strength, state, tally)
        state.updated_epoch = ctx.epoch
        tally.running += 1
    return tally


async def catastrophe(ctx: TickContext, work: EntityRow, profile: StructureProfileRow) -> list[str]:
    world = await host_world(ctx.session, profile)
    found = ["control core failed"]
    planet = await planet_of(ctx.session, world) if world is not None else None
    if profile.kind is K.PLANETARY_ENGINE and planet is not None and not held(planet.id) and "orbit" not in (planet.locked or []):
        planet.orbit = max(0.01, planet.orbit * (1 + ctx.rules.megastructures.engine_shock_pct / PERCENT))
        found.append("orbit thrown")
    if profile.kind is K.STAR_COLLECTOR and world is not None and world.star_id is not None:
        star = await ctx.session.get(StarRow, world.star_id)
        if star is not None and not held(star.id) and "brightness" not in (star.locked or []):
            star.brightness = clamp_int(star.brightness + ctx.rules.megastructures.collector_flare, 0, PERCENT)
            found.append("star flared")
    await record(
        ctx,
        "megastructures.catastrophe",
        roles={
            IncidentRole.SUBJECT: work.id,
            IncidentRole.VICTIM: [
                node for node in (planet.id if planet is not None else None, world.star_id if world is not None else None) if node is not None
            ],
        },
        facts={"structure": profile.kind, "orbit_thrown": int("orbit thrown" in found), "star_flared": int("star flared" in found)},
        place=work.location_id,
    )
    return found
