import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow, ThreadLinkRow, ThreadRow
from aerona.db.tables.routes import JourneyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ThreadLinkRole
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.travel import JourneyIntent, JourneyStatus, TravelMethod
from aerona.domain.enums.world import Atmosphere, Discovery, SkyEventKind, WorldType
from aerona.domain.models.entity_stats import MortalStats, PeopleStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.routes import JourneySpec, start_journey
from aerona.engine.phases.sky import SkyOrder, sky_event, spontaneous_bag, time_difference, time_echo, two_timed_hero
from aerona.engine.phases.travel import bridge_collapse, hidden_routes, journeys, kinship, route_knowledge, spontaneous_expeditions
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, make_route, make_son, make_world, teach, tick, tuned


def test_spontaneous_bag_order(rules: Rules) -> None:
    bag = spontaneous_bag(rules)
    assert bag == [
        SkyEventKind.ECLIPSE,
        SkyEventKind.COMET,
        SkyEventKind.COMET,
        SkyEventKind.ALIGNMENT,
        SkyEventKind.ECLIPSE,
        SkyEventKind.SUPERNOVA,
        SkyEventKind.BLACK_SUN,
        SkyEventKind.FLARE,
        SkyEventKind.FLARE,
    ]


async def test_eclipse_whispers_a_prophecy(ctx: TickContext, cosmos: Cosmos) -> None:
    people = await make_entity(ctx.session, "Tarn", EntityType.PEOPLE, PeopleStats(population=5000, piety=10), world_id=cosmos.home.id)
    result = await sky_event(ctx, SkyEventKind.ECLIPSE, SkyOrder(world_id=cosmos.home.id))
    assert "eclipse" in result.text
    assert people.sanity == ctx.rules.cosmic_horror.default_sanity - ctx.rules.sky.eclipse_sanity_loss
    assert people.stats.piety == 10 + ctx.rules.sky.eclipse_piety_gain
    prophecy = await ctx.session.scalar(select(EntityRow).where(EntityRow.entity_type == EntityType.PROPHECY))
    assert prophecy is not None
    assert await BondRepository(ctx.session).exists_between(people.id, prophecy.id, BondKind.PROPHESIES)
    assert await ctx.session.scalar(select(SkyEventRow)) is not None


async def test_comet_can_end_a_war(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "sky", comet_peace_chance=100))
    first = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id)
    second = await make_entity(session, "Vesk", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id)
    await BondRepository(session).connect(BondDraft(first.id, second.id, BondKind.ENEMY, 1, "old grudge"))
    result = await sky_event(ctx, SkyEventKind.COMET, SkyOrder(world_id=cosmos.home.id))
    assert "laid down arms" in result.text
    assert not await BondRepository(session).exists_between(first.id, second.id, BondKind.ENEMY)


async def test_creator_alignment_needs_something_to_open(ctx: TickContext, cosmos: Cosmos) -> None:
    with pytest.raises(ValidationFailedError):
        await sky_event(ctx, SkyEventKind.ALIGNMENT, SkyOrder(world_id=cosmos.home.id, by="Aeron"))
    other = await make_world(ctx.session, "Velmor")
    await make_route(ctx.session, cosmos.home.id, other.id, TravelMethod.SLINGSHOT_ORBIT, active=False)
    result = await sky_event(ctx, SkyEventKind.ALIGNMENT, SkyOrder(world_id=cosmos.home.id, by="Aeron"))
    assert "slingshot orbits opened" in result.text


async def test_forgotten_world_refuses_sky_events(ctx: TickContext, cosmos: Cosmos) -> None:
    other = await make_world(ctx.session, "Velmor")
    other.discovery = Discovery.FORGOTTEN
    with pytest.raises(ValidationFailedError):
        await sky_event(ctx, SkyEventKind.ECLIPSE, SkyOrder(world_id=other.id))


async def test_time_echo_brings_a_traveller(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "sky", time_traveler_share_pct=100))
    region = await make_region(session, "Coast", cosmos.home.id)
    thread = ThreadRow(epoch=1, text="An open story.")
    session.add(thread)
    await session.flush()
    session.add(ThreadLinkRow(thread_id=thread.id, entity_id=region.id, role=ThreadLinkRole.RELATED, epoch=1))
    await session.flush()
    traveller = await time_echo(ctx)
    assert traveller is not None and traveller.entity_type is EntityType.MORTAL and traveller.location_id == region.id


async def test_two_timed_hero_and_time_difference(ctx: TickContext, cosmos: Cosmos) -> None:
    hero = await make_entity(ctx.session, "Iska", EntityType.MORTAL, MortalStats(charisma=90, age=30, lifespan=70), world_id=cosmos.home.id)
    assert (await two_timed_hero(ctx)) is not None
    assert EntityFlag.TWO_TIMED in await EntityRepository(ctx.session).flags(hero.id)
    dream = await make_world(ctx.session, "Somnia", WorldType.DREAM)
    dream.time_factor = 3.0
    text = time_difference(ctx.rules, "Tarn", cosmos.home, dream, 2)
    assert text is not None and str(ctx.rules.time.years_per_epoch * 2 * 2) in text
    assert time_difference(ctx.rules, "Tarn", cosmos.home, cosmos.home, 2) is None


async def test_hidden_routes_reveal_with_certain_chance(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "travel", hidden_base_chance=100))
    other = await make_world(session, "Velmor")
    other.discovery = Discovery.LEGEND
    route = await make_route(session, cosmos.home.id, other.id, known=False)
    assert await hidden_routes(ctx) == 1
    assert route.known and other.discovery is Discovery.KNOWN


async def test_route_knowledge_is_learned(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "travel", route_knowledge_chance=100))
    other = await make_world(session, "Velmor")
    await make_route(session, cosmos.home.id, other.id, TravelMethod.ANCIENT_GATE)
    people = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=5000, craft=50), world_id=cosmos.home.id)
    assert await route_knowledge(ctx) == 1
    knowledge = await session.scalar(select(EntityRow).where(EntityRow.knowledge_branch == KnowledgeBranch.GATE_LORE))
    assert knowledge is not None and await BondRepository(session).exists_between(people.id, knowledge.id, BondKind.KNOWS)


async def test_bridge_collapses_when_builder_sleeps(ctx: TickContext, cosmos: Cosmos) -> None:
    other = await make_world(ctx.session, "Velmor")
    son = await make_son(ctx.session, "Velan", cosmos.home.id)
    bridge = await make_route(ctx.session, cosmos.home.id, other.id, TravelMethod.DIVINE_BRIDGE)
    bridge.builder_son_id = son.id
    son.status = SonStatus.ASLEEP
    assert await bridge_collapse(ctx) == 1 and not bridge.active


async def test_colony_journey_arrives_and_meets_natives(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(
        session, tuned(tuned(rules, "travel", colony_invasion_chance=0, contact_trade_chance=100, interworld_alliance_chance=0), "creatures", stowaway_chance=0)
    )
    other = await make_world(session, "Velmor")
    await make_region(session, "Green Vale", other.id, fertility=80)
    native = await make_entity(session, "Velfolk", EntityType.PEOPLE, PeopleStats(population=3000), world_id=other.id)
    people = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=8000, piety=40), world_id=cosmos.home.id)
    await teach(session, people, KnowledgeBranch.GATE_LORE)
    gate = await make_route(session, cosmos.home.id, other.id, TravelMethod.ANCIENT_GATE, duration=1)
    journey = await start_journey(ctx, JourneySpec(people, gate, JourneyIntent.COLONY, 1000))
    arrived = await journeys(ctx)
    assert arrived == [journey.id] and journey.status is JourneyStatus.ARRIVED
    colony = await session.get(EntityRow, journey.result_entity_id)
    assert colony is not None and colony.world_id == other.id and colony.stats.population == 1000
    assert await BondRepository(session).exists_between(people.id, colony.id, BondKind.RULES)
    assert await BondRepository(session).exists_between(people.id, native.id, BondKind.TRADES_WITH)
    assert colony.id in await kinship(session, people.id)


async def test_harsh_sky_kills_unprepared_colonies(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "creatures", stowaway_chance=0))
    other = await make_world(session, "Ashveil")
    other.atmosphere = Atmosphere.TOXIC
    await make_region(session, "Ash Flats", other.id)
    people = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=8000), world_id=cosmos.home.id)
    await teach(session, people, KnowledgeBranch.GATE_LORE)
    gate = await make_route(session, cosmos.home.id, other.id, TravelMethod.ANCIENT_GATE)
    journey = await start_journey(ctx, JourneySpec(people, gate, JourneyIntent.COLONY, 1000))
    await journeys(ctx)
    assert journey.status is JourneyStatus.ARRIVED and journey.result_entity_id is None
    texts = list(await session.scalars(select(ChronicleRow.text)))
    assert any("could not live" in text for text in texts)


async def test_spontaneous_expedition_needs_a_civilization(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "travel", expedition_base_pct=100))
    other = await make_world(session, "Velmor")
    await make_route(session, cosmos.home.id, other.id, TravelMethod.DIVINE_BRIDGE)
    people = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=50000), world_id=cosmos.home.id)
    assert await spontaneous_expeditions(ctx) == 0
    people.civ_tier = 1
    assert await spontaneous_expeditions(ctx) == 1
    journey = await session.scalar(select(JourneyRow))
    assert journey is not None and journey.traveller_entity_id == people.id


async def test_lone_dreamer_may_not_return(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(tuned(rules, "travel_methods", dream_lone_no_return_pct=100), "creatures", stowaway_chance=0))
    other = await make_world(session, "Somnia")
    await make_region(session, "Cloud", other.id)
    dreamer = await make_entity(session, "Iska", EntityType.MORTAL, MortalStats(age=30, lifespan=70), world_id=cosmos.home.id)
    await teach(session, dreamer, KnowledgeBranch.MAGIC)
    route = await make_route(session, cosmos.home.id, other.id, TravelMethod.DREAM_JOURNEY)
    await start_journey(ctx, JourneySpec(dreamer, route, JourneyIntent.EXPLORATION))
    await journeys(ctx)
    assert dreamer.status.value == "dead"
