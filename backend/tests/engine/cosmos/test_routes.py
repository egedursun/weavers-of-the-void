import pytest
from sqlalchemy import event, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.travel import JourneyIntent, JourneyStatus, RouteClosure, TravelMethod
from aerona.domain.enums.world import Discovery, WorldType
from aerona.domain.models.entity_stats import PeopleStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.routes import (
    JourneySpec,
    RouteBook,
    RouteSpec,
    RouteState,
    can_use_route,
    connect_all_worlds,
    connect_world,
    open_alignment,
    open_route,
    recall_journey,
    repair_route,
    route_status,
    sever_route,
    sky_calendar,
    snap_sail_routes,
    start_journey,
)
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, make_route, make_world, teach, tick, tuned


def test_calendar_aligns_on_the_cycle(rules: Rules) -> None:
    aligned = sky_calendar(rules, 10, None)
    closed = sky_calendar(rules, 7, None)
    assert aligned.aligned and aligned.closes_epoch == 11
    assert not closed.aligned and closed.opens_epoch == 10
    forced = sky_calendar(rules, 7, 9)
    assert forced.aligned and not forced.cycle_aligned and forced.closes_epoch == 9


async def test_route_status_priority(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    other = await make_world(session, "Velmor")
    route = await make_route(session, cosmos.home.id, other.id, TravelMethod.SLINGSHOT_ORBIT)
    calendar = sky_calendar(rules, 7, None)
    assert route_status(route, calendar, set()).state is RouteState.MISALIGNED
    route.active = False
    route.temp_closed_until_epoch = 9
    assert route_status(route, calendar, set()).state is RouteState.SEVERED
    assert route_status(route, calendar, {other.id}).state is RouteState.FORGOTTEN
    route.temp_closed_until_epoch = None
    route.closure = RouteClosure.SNAPPED
    assert route_status(route, calendar, set()).state is RouteState.SNAPPED
    route.closure = None
    assert route_status(route, calendar, set()).state is RouteState.SEALED


async def test_open_route_reuses_and_bounds_danger(ctx: TickContext, cosmos: Cosmos) -> None:
    other = await make_world(ctx.session, "Velmor", WorldType.ASTEROID_BELT)
    first = await open_route(ctx.session, ctx.rules, ctx.rng(), ctx.epoch, RouteSpec(cosmos.home.id, other.id, TravelMethod.ANCIENT_GATE, known=False))
    again = await open_route(ctx.session, ctx.rules, ctx.rng(), ctx.epoch, RouteSpec(other.id, cosmos.home.id, TravelMethod.ANCIENT_GATE))
    assert first.id == again.id and again.known
    assert ctx.rules.travel.route_danger_min <= first.danger <= ctx.rules.travel.route_danger_max
    with pytest.raises(ValidationFailedError):
        await open_route(ctx.session, ctx.rules, ctx.rng(), ctx.epoch, RouteSpec(other.id, other.id, TravelMethod.ANCIENT_GATE))


async def test_can_use_route_requirements(ctx: TickContext, cosmos: Cosmos) -> None:
    other = await make_world(ctx.session, "Velmor")
    people = await make_entity(ctx.session, "Tarn", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id)
    gate = await make_route(ctx.session, cosmos.home.id, other.id, TravelMethod.ANCIENT_GATE)
    river = await make_route(ctx.session, cosmos.home.id, other.id, TravelMethod.DEATH_CURRENT)
    sail = await make_route(ctx.session, cosmos.home.id, other.id, TravelMethod.LIGHT_SAIL)
    assert "gate lore" in (await can_use_route(ctx.session, ctx.rules, ctx.epoch, people, gate) or "")
    await teach(ctx.session, people, KnowledgeBranch.GATE_LORE)
    assert await can_use_route(ctx.session, ctx.rules, ctx.epoch, people, gate) is None
    assert "realm of the dead" in (await can_use_route(ctx.session, ctx.rules, ctx.epoch, people, river) or "")
    await teach(ctx.session, people, KnowledgeBranch.SHIPBUILDING)
    assert "ship" in (await can_use_route(ctx.session, ctx.rules, ctx.epoch, people, sail) or "")


async def test_start_journey_moves_people_and_charges_the_gate(ctx: TickContext, cosmos: Cosmos) -> None:
    other = await make_world(ctx.session, "Velmor")
    people = await make_entity(ctx.session, "Tarn", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id)
    gate = await make_route(ctx.session, cosmos.home.id, other.id, TravelMethod.ANCIENT_GATE, duration=1)
    journey = await start_journey(ctx, JourneySpec(people, gate, JourneyIntent.COLONY, 1000))
    assert people.stats.population == 4000
    sacrificed = round(1000 * ctx.rules.travel_methods.gate_sacrifice_pct / 100)
    assert journey.population == 1000 - sacrificed
    assert journey.events and journey.events[0].loss == sacrificed
    assert journey.epochs_left == 1 and journey.destination_world_id == other.id
    text = await recall_journey(ctx, journey.id, "The Creator")
    assert journey.status is JourneyStatus.RECALLED and "returned home" in text
    assert people.stats.population == 4000 + journey.population


async def test_sever_and_stitch(ctx: TickContext, cosmos: Cosmos) -> None:
    other = await make_world(ctx.session, "Velmor")
    route = await make_route(ctx.session, cosmos.home.id, other.id, known=False)
    rules = tuned(ctx.rules, "beyond", storm_reveal_chance=100, storm_loss_chance=0)
    storm_ctx = tick(ctx.session, rules, phase="storm")
    people = await make_entity(ctx.session, "Tarn", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id)
    ctx.session.add(
        JourneyRow(
            traveller_entity_id=people.id,
            route_id=route.id,
            origin_world_id=cosmos.home.id,
            destination_world_id=other.id,
            intent=JourneyIntent.TRADE,
            epochs_left=2,
            start_epoch=1,
        )
    )
    await ctx.session.flush()
    result = await sever_route(storm_ctx, route.id, duration=3, by="The Creator")
    assert result.revealed and route.known and not route.active and result.waiting == 1
    assert route.temp_closed_until_epoch == ctx.epoch + 3
    text = await repair_route(ctx, route.id, "The Creator")
    assert route.active and "reopened the severed route" in text


async def test_alignment_reveals_and_unseals(ctx: TickContext, cosmos: Cosmos) -> None:
    other = await make_world(ctx.session, "Velmor")
    hidden = await make_route(ctx.session, cosmos.home.id, other.id, TravelMethod.LIGHT_SAIL, known=False)
    sealed = await make_route(ctx.session, cosmos.home.id, other.id, TravelMethod.SLINGSHOT_ORBIT, active=False)
    revealed = await open_alignment(ctx, [TravelMethod.SLINGSHOT_ORBIT], duration=2)
    assert revealed == 1 and hidden.known
    assert sealed.active and sealed.temp_open_until_epoch == ctx.epoch + 2
    book = await RouteBook.load(ctx.session, ctx.rules, ctx.epoch)
    assert book.status(sealed).state is RouteState.TEMPORARY


async def test_connect_world_stitches_isolated_worlds(ctx: TickContext, cosmos: Cosmos) -> None:
    dead = await make_world(ctx.session, "Nethis", WorldType.DEAD)
    route = await connect_world(ctx, dead)
    assert route is not None and not route.known and route.method is TravelMethod.DEATH_CURRENT
    assert await connect_world(ctx, dead) is None


async def test_star_death_snaps_sails(ctx: TickContext, cosmos: Cosmos) -> None:
    other = await make_world(ctx.session, "Velmor")
    sail = await make_route(ctx.session, cosmos.home.id, other.id, TravelMethod.LIGHT_SAIL)
    assert await snap_sail_routes(ctx, cosmos.star.id) == 1
    assert not sail.active and sail.closure is RouteClosure.SNAPPED


async def test_forgetting_closes_and_remembering_reopens(session: AsyncSession, cosmos: Cosmos) -> None:
    other = await make_world(session, "Velmor")
    route = await make_route(session, cosmos.home.id, other.id)
    repository = WorldRepository(session)
    await repository.set_discovery(other, Discovery.FORGOTTEN)
    assert not route.active and route.closed_by_forgetting_world_id == other.id
    await repository.set_discovery(other, Discovery.KNOWN)
    assert route.active
    routes = list(await session.scalars(select(RouteRow)))
    assert len(routes) == 1


async def test_trade_with_controller_waives_knowledge(ctx: TickContext, cosmos: Cosmos) -> None:
    other = await make_world(ctx.session, "Velmor")
    await make_region(ctx.session, "Coast", cosmos.home.id)
    people = await make_entity(ctx.session, "Tarn", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id)
    keeper = await make_entity(ctx.session, "Keepers", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id)
    gate = await make_route(ctx.session, cosmos.home.id, other.id)
    gate.controller_entity_id = keeper.id
    await BondRepository(ctx.session).connect(BondDraft(people.id, keeper.id, BondKind.TRADES_WITH, 1))
    assert await can_use_route(ctx.session, ctx.rules, ctx.epoch, people, gate) is None


async def test_connecting_every_unrouted_world_reads_the_cosmos_once(session: AsyncSession, cosmos: Cosmos, ctx: TickContext) -> None:
    worlds = [await make_world(session, f"Drift {index}", star_id=cosmos.star.id) for index in range(30)]
    seen: list[str] = []
    event.listen(session.sync_session.bind, "before_cursor_execute", lambda *args: seen.append(args[2]))
    assert await connect_all_worlds(ctx) > 0
    for world in [cosmos.home, *worlds]:
        assert await session.scalar(select(RouteRow.id).where(or_(RouteRow.world_a_id == world.id, RouteRow.world_b_id == world.id)).limit(1)) is not None
    assert len(seen) < 12 * (len(worlds) + 1)
