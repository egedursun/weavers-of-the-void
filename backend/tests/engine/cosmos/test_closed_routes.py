import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.travel import JourneyIntent, JourneyStatus, RouteClosure, TravelMethod
from aerona.domain.models.entity_stats import PeopleStats
from aerona.engine.cosmos.routes import JourneySpec, _closed_status, start_journey
from aerona.engine.phases.travel import LOST_REASONS, journeys
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, make_route, make_world, teach, tick, tuned


async def under_way(session: AsyncSession, cosmos: Cosmos, rules: Rules, method: TravelMethod) -> tuple[JourneyRow, RouteRow, object]:
    ctx = tick(session, tuned(rules, "creatures", stowaway_chance=0))
    other = await make_world(session, "Velmor")
    await make_region(session, "Green Vale", other.id, fertility=80)
    people = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=8000, piety=40, prosperity=40), world_id=cosmos.home.id)
    await teach(session, people, KnowledgeBranch.GATE_LORE)
    route = await make_route(session, cosmos.home.id, other.id, method, duration=3)
    journey = await start_journey(ctx, JourneySpec(people, route, JourneyIntent.COLONY, 1000))
    return journey, route, ctx


async def keys(session: AsyncSession) -> list[str | None]:
    return list(await session.scalars(select(ChronicleRow.template_key)))


@pytest.mark.parametrize("closure", [RouteClosure.SEVERED, RouteClosure.SCORCHED])
async def test_travellers_wait_out_a_route_shut_for_a_while(session: AsyncSession, cosmos: Cosmos, rules: Rules, closure: RouteClosure) -> None:
    journey, route, ctx = await under_way(session, cosmos, rules, TravelMethod.ANCIENT_GATE)
    route.active, route.closure, route.temp_closed_until_epoch = False, closure, 9
    await journeys(ctx)
    assert journey.status is JourneyStatus.WAITING and journey.end_epoch is None
    assert "travel.waiting" in await keys(session)
    texts = list(await session.scalars(select(ChronicleRow.text).where(ChronicleRow.template_key == "travel.waiting")))
    assert texts and all("road" not in text for text in texts)


@pytest.mark.parametrize(
    ("closure", "reason"),
    [(RouteClosure.SEALED, "sealed"), (RouteClosure.SNAPPED, "sail snapped"), (RouteClosure.COLLAPSED, "bridge collapsed")],
)
async def test_travellers_are_lost_on_a_route_shut_for_good(session: AsyncSession, cosmos: Cosmos, rules: Rules, closure: RouteClosure, reason: str) -> None:
    journey, route, ctx = await under_way(session, cosmos, rules, TravelMethod.ANCIENT_GATE)
    route.active, route.closure, route.temp_closed_until_epoch = False, closure, None
    await journeys(ctx)
    assert journey.status is JourneyStatus.LOST and journey.end_epoch is not None
    vanished = list(await session.scalars(select(ChronicleRow.text).where(ChronicleRow.template_key == "travel.journey_vanished")))
    assert vanished and reason in vanished[0]


@pytest.mark.parametrize("closure", list(RouteClosure))
def test_every_closure_either_reopens_or_names_why_travellers_were_lost(closure: RouteClosure) -> None:
    for until in (None, 9):
        route = RouteRow(world_a_id=1, world_b_id=2, method=TravelMethod.ANCIENT_GATE, active=False, closure=closure, temp_closed_until_epoch=until)
        closed = _closed_status(route, {2} if closure is RouteClosure.FORGOTTEN else set())
        assert closed is not None
        state, _, opens = closed
        assert opens is not None or state in LOST_REASONS
