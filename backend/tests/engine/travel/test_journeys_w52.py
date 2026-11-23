from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life_traits import JOURNEY_INTENT_TRAITS
from aerona.catalog.travel import JOURNEY_INTENT_LABELS
from aerona.core.random import SeededRandom
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.travel import JourneyIntent, TravelMethod
from aerona.domain.models.entity_stats import PeopleStats
from aerona.engine.cosmos.routes import JourneySpec, start_journey
from aerona.engine.phases.travel import choose_intent, journeys
from aerona.engine.primitives.stats import stat_or
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, make_route, make_world, teach, tick, tuned


def test_the_unruly_the_beset_and_the_neighbourly_send_exiles_refugees_and_envoys() -> None:
    rules = tuned(Rules(), "travel", exile_intent_chance=100, flight_intent_chance=100, embassy_intent_chance=100)
    rng = SeededRandom.for_epoch(1, 1, "intent")
    assert choose_intent(rules, rng, 0, True, unruly=True) is JourneyIntent.EXILE
    assert choose_intent(rules, rng, 0, True, beset=True) is JourneyIntent.FLIGHT
    assert choose_intent(rules, rng, 0, False) is JourneyIntent.EMBASSY
    for intent in JourneyIntent:
        assert JOURNEY_INTENT_LABELS[intent] and intent in JOURNEY_INTENT_TRAITS


async def voyage(session: AsyncSession, cosmos: Cosmos, intent: JourneyIntent, *, native: bool) -> tuple[EntityRow, EntityRow | None]:
    ctx = tick(session, tuned(tuned(Rules(), "creatures", stowaway_chance=0), "travel", lost_chance=0))
    other = await make_world(session, "Velmor")
    await make_region(session, "Green Vale", other.id, fertility=80)
    folk = await make_entity(session, "Velfolk", EntityType.PEOPLE, PeopleStats(population=3000, prosperity=30), world_id=other.id) if native else None
    people = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=8000, prosperity=40), world_id=cosmos.home.id)
    await teach(session, people, KnowledgeBranch.GATE_LORE)
    gate = await make_route(session, cosmos.home.id, other.id, TravelMethod.ANCIENT_GATE, duration=1)
    await start_journey(ctx, JourneySpec(people, gate, intent, 1000))
    await journeys(ctx)
    return people, folk


async def test_exiles_found_a_settlement_their_old_home_does_not_rule(session: AsyncSession, cosmos: Cosmos) -> None:
    people, _ = await voyage(session, cosmos, JourneyIntent.EXILE, native=False)
    colony = await session.scalar(select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.world_id != cosmos.home.id))
    assert colony is not None
    assert not await BondRepository(session).active_between(people.id, colony.id, [BondKind.RULES])


async def test_an_embassy_carries_a_gift_and_opens_relations(session: AsyncSession, cosmos: Cosmos) -> None:
    people, folk = await voyage(session, cosmos, JourneyIntent.EMBASSY, native=True)
    assert folk is not None
    received = await session.scalar(select(IncidentRow).where(IncidentRow.kind == "travel.embassy_received"))
    assert received is not None
    assert stat_or(folk, "prosperity", 0) > 30 and stat_or(people, "prosperity", 0) < 40
