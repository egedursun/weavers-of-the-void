from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.military import LEVELS
from aerona.catalog.life.polity import MODEL_PENALTIES
from aerona.db.tables.culture import IdeologyAdherentRow, IdeologyProfileRow, IdeologyTenetRow, ProphecyConditionRow
from aerona.db.tables.environment import WorldSeasonRow
from aerona.db.tables.folkways import BiasWeightRow, DietRow
from aerona.db.tables.made import AugmentRow
from aerona.db.tables.military import FeudRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.routes import JourneyRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.db.tables.thin_sections import JourneyEncounterRow, RelationComponentRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import IdeologyTenet, ProphecyPredicate, ProphecyState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.folkways import BiasedDecision, DecisionBias, ImpuritySource
from aerona.domain.enums.happening import EventPhase
from aerona.domain.enums.military import FeudAction, FeudLevel
from aerona.domain.enums.mind import HonourModel, RelationComponent
from aerona.domain.enums.polity import OathPenalty
from aerona.domain.enums.travel import ArrivalOutcome, EncounterEffect, JourneyIntent, RouteEnvironment, TravelMethod
from aerona.domain.models.entity_stats import CelestialStats, IdeologyStats, PeopleStats, ProphecyStats
from aerona.engine.cosmos.encounters import ENVIRONMENTS, arrive, provision, seed_encounters
from aerona.engine.cosmos.omens import seen_by
from aerona.engine.folkways.biases import PUSHES, lean
from aerona.engine.folkways.nutrition import lean_season, season_and_craft
from aerona.engine.folkways.purity import TOUCHES, Touch, by_augment
from aerona.engine.happenings.progression import PHASE_STEPS
from aerona.engine.interconnect.registry import MECHANICS
from aerona.engine.lore.creed_change import merge_creeds
from aerona.engine.lore.prophecy_tales import retell
from aerona.engine.military.feud_acts import raise_level
from aerona.engine.mind.relation_parts import keep_relation_components
from aerona.engine.polity.oath_terms import scaled_loss
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.services.community_relations import pair_key
from tests.engine.core.factories import CoreWorld, bond, entity, mortal
from tests.engine.core.test_minds_w44 import at


async def test_nutrition_lean_season_takes_fresh_food_and_medicine_fortifies(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 2)
    session.add(WorldSeasonRow(world_id=world.world.id, position=9, name="Thin Months", temperature_shift=0, rain_shift=0, growth=10, travel=0, campaign=0))
    await session.flush()
    assert await lean_season(ctx, world.world.id) == 40
    diet = DietRow(holder_node_id=world.people.id, fresh=30, preserved=0, mineral=5, locked=[])
    await season_and_craft(ctx, world.people, diet)
    assert diet.fresh < 30


async def test_biases_reach_the_new_decisions(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 2)
    assert set(PUSHES) == set(BiasedDecision)
    leader = await mortal(session, "Orsa", world, world.regions[0].id)
    session.add(BiasWeightRow(holder_node_id=leader.id, bias=DecisionBias.OVERCONFIDENCE, weight=100, last_shift=0, locked=[]))
    await session.flush()
    assert await lean(ctx, leader.id, BiasedDecision.WAR) > 1


async def test_purity_reads_augments(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 2)
    assert set(TOUCHES) == set(ImpuritySource)
    bearer = await mortal(session, "Ivo", world, world.regions[0].id)
    touch = Touch(ctx, bearer, MortalProfileRow(entity_id=bearer.id), world.people.id)
    assert not await by_augment(touch)
    session.add(AugmentRow(bearer_node_id=bearer.id, installed_epoch=1))
    await session.flush()
    assert await by_augment(touch)


async def test_two_creeds_merge_into_one(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 2)
    creeds = []
    for name, tenet in (("First Word", IdeologyTenet.LEGALISM), ("Second Word", IdeologyTenet.RATIONALISM)):
        creed = await entity(session, name, EntityType.IDEOLOGY, IdeologyStats(), world_id=world.world.id)
        session.add(IdeologyProfileRow(ideology_entity_id=creed.id, texts=[], locked=[]))
        session.add(IdeologyTenetRow(ideology_entity_id=creed.id, tenet=tenet))
        creeds.append(creed)
    session.add(IdeologyAdherentRow(ideology_entity_id=creeds[1].id, adherent_entity_id=world.people.id, strength=40, state=False))
    await session.flush()
    await merge_creeds(ctx, creeds[0].id, creeds[1].id)
    tenets = set(await session.scalars(select(IdeologyTenetRow.tenet).where(IdeologyTenetRow.ideology_entity_id == creeds[0].id)))
    assert tenets == {IdeologyTenet.LEGALISM, IdeologyTenet.RATIONALISM}
    assert await session.get(IdeologyAdherentRow, (creeds[0].id, world.people.id)) is not None
    assert creeds[1].status is EntityStatus.DESTROYED


async def test_a_prophecy_changes_in_the_telling(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3, prophecy={"retell_chance": 100, "retell_epochs": 2})
    told = await entity(session, "The Long Saying", EntityType.PROPHECY, ProphecyStats(), world_id=world.world.id)
    row = ProphecyConditionRow(prophecy_entity_id=told.id, predicate=ProphecyPredicate.WITHIN_EPOCHS, args={}, deadline_epoch=10)
    row.audience, row.state, row.locked = [world.people.id], ProphecyState.PENDING, []
    session.add(row)
    await session.flush()
    assert await retell(ctx, row)
    assert row.retold == 1


def test_every_event_phase_is_told_and_ends_in_memory() -> None:
    assert set(PHASE_STEPS) == set(EventPhase)
    assert EventPhase.MEMORY in PHASE_STEPS


async def test_a_body_hidden_from_view_is_not_read(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 2)
    atlas = await RegionAtlas.load(session)
    dim = await entity(session, "Faint Light", EntityType.CELESTIAL, CelestialStats(visibility=0), world_id=world.world.id)
    bright = await entity(session, "Clear Light", EntityType.CELESTIAL, CelestialStats(visibility=100), world_id=world.world.id)
    assert not await seen_by(ctx, dim, world.people, atlas)
    assert await seen_by(ctx, bright, world.people, atlas)


async def test_a_relation_is_broken_into_its_parts(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 2)
    other = await entity(session, "Far Folk", EntityType.PEOPLE, PeopleStats(), world_id=world.world.id)
    low, high = pair_key(world.people.id, other.id)
    session.add(CommunityRelationRow(entity_a_id=low, entity_b_id=high, value=0))
    await bond(session, low, high, BondKind.TRADES_WITH)
    await session.flush()
    await keep_relation_components(ctx)
    trade = await session.get(RelationComponentRow, (low, high, RelationComponent.TRADE))
    assert trade is not None and trade.value == ctx.rules.community_relations.trade_value


def test_oath_penalties_follow_the_honour_model() -> None:
    assert set(MODEL_PENALTIES) == set(HonourModel)
    assert MODEL_PENALTIES[HonourModel.NONE] is None
    assert MODEL_PENALTIES[HonourModel.HONOUR] is OathPenalty.SHAME
    assert scaled_loss(20, 150) == 30


def test_a_feud_climbs_the_ladder() -> None:
    assert set(LEVELS) == set(FeudAction)
    row = FeudRow(intensity=10, level=None, locked=[])
    raise_level(row, None, 30)
    assert row.level is FeudLevel.INSULT
    raise_level(row, FeudAction.RAID, 30)
    assert row.level is FeudLevel.RAID
    row.locked = ["level"]
    raise_level(row, FeudAction.ESCALATE, 30)
    assert row.level is FeudLevel.RAID


def test_conflict_is_joined_to_the_new_subsystems() -> None:
    mechanic = MECHANICS["conflict_couplings"]
    assert len(mechanic.couplings) == 8


async def test_journeys_meet_typed_encounters_and_arrive_by_outcome(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 5)
    assert set(ENVIRONMENTS) == set(TravelMethod)
    assert await seed_encounters(ctx) == len(RouteEnvironment) * len(EncounterEffect)
    await session.flush()
    assert int(await session.scalar(select(func.count(JourneyEncounterRow.id))) or 0) == len(RouteEnvironment) * len(EncounterEffect)
    journey = JourneyRow(intent=JourneyIntent.COLONY, population=100, supplies=10, births=0, deaths=0, start_epoch=1, epochs_left=2, events=[], locked=[])
    await provision(ctx, journey)
    assert journey.supplies == 0
    journey.population, journey.deaths = 20, 80
    assert await arrive(ctx, journey, None) is ArrivalOutcome.REFUGEES
