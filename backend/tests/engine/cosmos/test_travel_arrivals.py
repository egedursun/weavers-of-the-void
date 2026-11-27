import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.records import IncidentStepRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction, StepOutcome
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.travel import JourneyEventKind, JourneyIntent, JourneyStatus, TravelMethod
from aerona.domain.models.entity_stats import ItemStats, MortalStats, PeopleStats, ResourceStats, SpeciesStats
from aerona.engine.cosmos.routes import JourneySpec, start_journey
from aerona.engine.phases import travel as travel_module
from aerona.engine.phases.travel import journeys
from aerona.engine.services.community_relations import change_relation, relation
from aerona.engine.services.war import hostility_reason
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, make_route, make_world, teach, tick, tuned


async def role_holders(session: AsyncSession, kind: str, *roles: IncidentRole) -> set[int]:
    rows = await session.scalars(
        select(IncidentParticipantRow.node_id)
        .join(IncidentRow, IncidentRow.id == IncidentParticipantRow.incident_id)
        .where(IncidentRow.kind == kind, IncidentParticipantRow.role.in_(roles))
    )
    return set(rows)


async def meeting(session: AsyncSession, native_id: int) -> StepOutcome | None:
    return await session.scalar(
        select(IncidentStepRow.outcome)
        .join(IncidentRow, IncidentRow.id == IncidentStepRow.incident_id)
        .where(IncidentRow.kind == "travel.arrival", IncidentStepRow.action == StepAction.MEET, IncidentStepRow.target_node_id == native_id)
    )


async def chronicle_texts(session: AsyncSession) -> list[str]:
    return list(await session.scalars(select(ChronicleRow.text)))


async def voyage(
    session: AsyncSession, cosmos: Cosmos, rules: Rules, intent: JourneyIntent, *, native: bool = True, duration: int = 1, **tuning: dict[str, int]
) -> tuple[EntityRow, EntityRow | None, int, object]:
    tuned_rules = tuned(rules, "creatures", stowaway_chance=0)
    for namespace, values in tuning.items():
        tuned_rules = tuned(tuned_rules, namespace, **values)
    ctx = tick(session, tuned_rules)
    other = await make_world(session, "Velmor")
    await make_region(session, "Green Vale", other.id, fertility=80)
    folk = await make_entity(session, "Velfolk", EntityType.PEOPLE, PeopleStats(population=3000), world_id=other.id) if native else None
    people = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=8000, piety=40, prosperity=40), world_id=cosmos.home.id)
    await teach(session, people, KnowledgeBranch.GATE_LORE)
    gate = await make_route(session, cosmos.home.id, other.id, TravelMethod.ANCIENT_GATE, duration=duration)
    journey = await start_journey(ctx, JourneySpec(people, gate, intent, 1000))
    return people, folk, journey.id, ctx


async def test_a_lost_way_costs_people_but_not_time(session: AsyncSession, cosmos: Cosmos, rules: Rules, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(travel_module, "COMMON_EVENTS", (JourneyEventKind.LOST_WAY,))
    people, _, journey_id, ctx = await voyage(session, cosmos, rules, JourneyIntent.COLONY, duration=3, travel={"lost_chance": 0})
    route = await session.scalar(select(RouteRow))
    assert route is not None
    route.danger = 100
    await journeys(ctx)
    journey = await session.get(JourneyRow, journey_id)
    assert journey is not None and journey.status is JourneyStatus.UNDERWAY
    assert journey.epochs_left == 2
    assert journey.population < 1000
    assert people.id


async def test_a_lost_vehicle_becomes_a_ghost_ship_legend(session: AsyncSession, cosmos: Cosmos, rules: Rules, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(travel_module, "COMMON_EVENTS", (JourneyEventKind.LOST_WAY,))
    people, _, journey_id, ctx = await voyage(session, cosmos, rules, JourneyIntent.COLONY, duration=3, travel={"lost_chance": 100})
    journey = await session.get(JourneyRow, journey_id)
    assert journey is not None
    vessel = await make_entity(session, "Swift Keel", EntityType.ITEM, ItemStats(), world_id=cosmos.home.id)
    journey.vehicle_entity_id = vessel.id
    route = await session.get(RouteRow, journey.route_id)
    assert route is not None
    route.danger = 100
    await journeys(ctx)
    assert people.id
    assert journey.status is JourneyStatus.LOST
    assert vessel.status is not EntityStatus.CANON
    lost = await session.scalar(select(EntityRow).where(EntityRow.entity_type == EntityType.LEGEND, EntityRow.name == "Swift Keel, the Lost Vessel"))
    assert lost is not None
    assert lost.id in await role_holders(session, "travel.vanished", IncidentRole.PRODUCT)


async def test_a_stowaway_species_invades_the_landing_region(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    _, _, journey_id, ctx = await voyage(session, cosmos, rules, JourneyIntent.COLONY, creatures={"stowaway_chance": 100})
    await make_entity(session, "Ash Hare", EntityType.SPECIES, SpeciesStats(danger=5), world_id=cosmos.home.id)
    await journeys(ctx)
    invader = await session.scalar(select(EntityRow).where(EntityRow.name == "Ash Hare (stowaway)"))
    journey = await session.get(JourneyRow, journey_id)
    assert journey is not None and invader is not None
    assert invader.world_id == journey.destination_world_id
    assert await EntityRepository(session).has_flag(invader.id, EntityFlag.INVASIVE)
    assert invader.id in await role_holders(session, "travel.stowaway", IncidentRole.SUBJECT, IncidentRole.ACTOR, IncidentRole.PRODUCT)
    assert JourneyEventKind.STOWAWAY in {event.kind for event in journey.events}


async def test_exploration_raises_charisma_and_finds_the_original_resource_and_land(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(tuned(tuned(rules, "creatures", stowaway_chance=0), "travel", exploration_land_chance=100), "exploration", new_region_pct=100))
    other = await make_world(session, "Velmor")
    await make_region(session, "Green Vale", other.id, fertility=80)
    original = await make_entity(session, "Moon Salt", EntityType.RESOURCE, ResourceStats(abundance=50), world_id=other.id)
    await EntityRepository(session).add_flag(original.id, EntityFlag.ORIGINAL_RESOURCE, 1)
    explorer = await make_entity(session, "Iska", EntityType.MORTAL, MortalStats(age=30, lifespan=70, charisma=40), world_id=cosmos.home.id)
    await teach(session, explorer, KnowledgeBranch.GATE_LORE)
    gate = await make_route(session, cosmos.home.id, other.id, TravelMethod.ANCIENT_GATE)
    journey = await start_journey(ctx, JourneySpec(explorer, gate, JourneyIntent.EXPLORATION))
    await journeys(ctx)
    assert journey.status is JourneyStatus.ARRIVED
    assert explorer.stats.charisma > 40
    assert await BondRepository(session).exists_between(explorer.id, original.id, BondKind.DISCOVERED)
    land = await session.get(EntityRow, journey.result_entity_id)
    assert land is not None and land.world_id == other.id and await EntityRepository(session).has_flag(land.id, EntityFlag.DISCOVERY)
    assert [event.kind for event in journey.events if event.kind is JourneyEventKind.DISCOVERY] == [JourneyEventKind.DISCOVERY] * 2


async def test_a_trade_expedition_adds_prosperity(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    people, _, _, ctx = await voyage(session, cosmos, rules, JourneyIntent.TRADE, native=False)
    before = people.stats.prosperity
    await journeys(ctx)
    assert people.stats.prosperity > before


async def test_conquest_is_seen_as_invasion_and_opens_a_war(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    people, folk, _, ctx = await voyage(session, cosmos, rules, JourneyIntent.CONQUEST)
    assert folk is not None
    await journeys(ctx)
    journey = await session.scalar(select(JourneyRow))
    assert journey is not None
    outpost = await session.get(EntityRow, journey.result_entity_id)
    assert outpost is not None
    assert await BondRepository(session).exists_between(outpost.id, folk.id, BondKind.ENEMY)
    assert await relation(session, ctx.rules, people.id, folk.id) < 0
    assert await meeting(session, folk.id) is StepOutcome.REFUSED
    assert await hostility_reason(session, outpost.id, folk.id) == "first contact: invasion"


async def test_uneasy_first_contact_lowers_the_relation_slightly(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    people, folk, _, ctx = await voyage(session, cosmos, rules, JourneyIntent.EXPLORATION, travel={"contact_trade_chance": 0})
    assert folk is not None
    before = await relation(session, ctx.rules, people.id, folk.id)
    await journeys(ctx)
    assert await relation(session, ctx.rules, people.id, folk.id) == before - ctx.rules.travel.uneasy_relation_loss
    assert await meeting(session, folk.id) is StepOutcome.DELAYED
    assert not await BondRepository(session).exists_between(people.id, folk.id, BondKind.TRADES_WITH)


async def test_friendly_first_contact_exchanges_culture_both_ways(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    people, folk, _, ctx = await voyage(
        session,
        cosmos,
        rules,
        JourneyIntent.TRADE,
        culture={"first_knowledge_pct": 100},
        travel={"interworld_alliance_chance": 0},
    )
    assert folk is not None
    brought = await teach(session, people, KnowledgeBranch.MAGIC)
    native_lore = await teach(session, folk, KnowledgeBranch.MEDICINE)
    await journeys(ctx)
    bonds = BondRepository(session)
    assert await bonds.exists_between(people.id, folk.id, BondKind.TRADES_WITH)
    assert await bonds.exists_between(folk.id, brought.id, BondKind.KNOWS)
    assert await bonds.exists_between(people.id, native_lore.id, BondKind.KNOWS)
    assert people.id in await role_holders(session, "culture.contact", IncidentRole.ACTOR, IncidentRole.TARGET)


async def test_an_invasion_is_a_first_contact_only_between_peoples_who_never_met(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    people, folk, _, ctx = await voyage(session, cosmos, rules, JourneyIntent.CONQUEST)
    assert folk is not None
    await change_relation(ctx, people.id, folk.id, -1, MemoryKind.ILL_WILL, note="uneasy first contact")
    await journeys(ctx)
    journey = await session.scalar(select(JourneyRow))
    assert journey is not None and journey.result_entity_id is not None
    assert await hostility_reason(session, journey.result_entity_id, folk.id) == "invasion from beyond the world"
