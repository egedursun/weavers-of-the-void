from dataclasses import replace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.achievements import ACHIEVEMENTS
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.worlds import StarDraft, WorldRepository
from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.lore import LegendaryQuestRow, MessageRow, ThreadRow
from aerona.db.tables.meta import ScenarioRow
from aerona.db.tables.routes import HorizonIntuitionRow, JourneyRow, RouteRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import LegendaryQuestKind, LegendaryQuestOutcome
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.meta import AchievementKey, ScenarioKey, ScenarioStatus
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.travel import HorizonStatus, JourneyIntent, JourneyStatus, TravelMethod
from aerona.domain.enums.world import StarType
from aerona.engine.gods import goals as goals_module
from aerona.engine.gods.goals import achieved, evaluate_goals, measure, safe_measure
from aerona.rules.registry import Rules
from aerona.services.gods.goals import start_scenario
from tests.engine.gods.factories import GodsWorld, add_world, bond, make_context, make_entity, make_son


def _goals(rules: Rules, **changes: int) -> Rules:
    return replace(rules, goals=replace(rules.goals, **changes))


async def _reached(session: AsyncSession, rules: Rules, key: AchievementKey, epoch: int = 3) -> bool:
    return await achieved(session, rules, key, epoch)


async def _star(session: AsyncSession, name: str, star_type: StarType) -> None:
    await WorldRepository(session).create_star(StarDraft(name, star_type, 50, 1.0, 1.0, 1))


async def _route(session: AsyncSession, first_id: int, second_id: int) -> RouteRow:
    route = RouteRow(world_a_id=first_id, world_b_id=second_id, method=TravelMethod.LIGHT_SAIL, duration_epochs=2, danger=10, created_epoch=1)
    session.add(route)
    await session.flush()
    return route


def test_every_achievement_has_a_condition() -> None:
    assert set(goals_module.CONDITIONS) == set(ACHIEVEMENTS)


async def test_second_sky_needs_the_threshold_of_worlds(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    assert not await _reached(session, rules, AchievementKey.SECOND_SKY)
    await add_world(session, "Kesh")
    assert await _reached(session, rules, AchievementKey.SECOND_SKY)


async def test_constellation_needs_the_threshold_of_stars(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _goals(rules, ach_stars=3)
    assert not await _reached(session, tuned, AchievementKey.CONSTELLATION)
    await _star(session, "Alpha", StarType.RED_GIANT)
    await _star(session, "Beta", StarType.PULSAR)
    assert await _reached(session, tuned, AchievementKey.CONSTELLATION)


async def test_prophecy_fulfilled_needs_a_fulfilled_prophecy(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    prophecy = await make_entity(session, "The Drowned Bell", EntityType.PROPHECY, world_id=world.world.id)
    assert not await _reached(session, rules, AchievementKey.PROPHECY_FULFILLED)
    prophecy.status = EntityStatus.FULFILLED
    await session.flush()
    assert await _reached(session, rules, AchievementKey.PROPHECY_FULFILLED)


async def test_fathers_hand_counts_only_a_successful_suppression(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    session.add(ActionRecordRow(epoch=2, actor_kind=ActorKind.CREATOR, actor_node_id=world.creator.id, kind=ActionKind.SUPPRESS_FAILED))
    await session.flush()
    assert not await _reached(session, rules, AchievementKey.FATHERS_HAND)
    session.add(ActionRecordRow(epoch=2, actor_kind=ActorKind.CREATOR, actor_node_id=world.creator.id, kind=ActionKind.SUPPRESS_REBELLION))
    await session.flush()
    assert await _reached(session, rules, AchievementKey.FATHERS_HAND)


async def test_babel_needs_the_threshold_of_languages(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _goals(rules, ach_languages=2)
    await make_entity(session, "Old Tongue", EntityType.LANGUAGE, world_id=world.world.id)
    assert not await _reached(session, tuned, AchievementKey.BABEL)
    await make_entity(session, "New Tongue", EntityType.LANGUAGE, world_id=world.world.id)
    assert await _reached(session, tuned, AchievementKey.BABEL)


async def test_crowded_world_needs_the_total_population(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id)
    assert not await _reached(session, _goals(rules, ach_population=6001), AchievementKey.CROWDED_WORLD)
    assert await _reached(session, _goals(rules, ach_population=6000), AchievementKey.CROWDED_WORLD)


async def test_first_prayer_needs_a_prayer_to_the_creator(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    mortal = await make_entity(session, "Asha", EntityType.MORTAL, world_id=world.world.id)
    son = await make_son(session, "Velkar", world.world.id)
    session.add(MessageRow(epoch=2, sender_node_id=mortal.id, recipient_node_id=son.id, intent=MessageIntent.PRAYER, text="Hear me."))
    await session.flush()
    assert not await _reached(session, rules, AchievementKey.FIRST_PRAYER)
    session.add(MessageRow(epoch=2, sender_node_id=mortal.id, recipient_node_id=world.creator.id, intent=MessageIntent.PRAYER, text="Hear me."))
    await session.flush()
    assert await _reached(session, rules, AchievementKey.FIRST_PRAYER)


async def test_creators_cult_needs_communities_worshipping_the_creator(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _goals(rules, ach_cult=2)
    first = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    second = await make_entity(session, "Bralk", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    await bond(session, first.id, world.creator.id, BondKind.WORSHIPS)
    assert not await _reached(session, tuned, AchievementKey.CREATORS_CULT)
    await bond(session, second.id, world.creator.id, BondKind.WORSHIPS)
    assert await _reached(session, tuned, AchievementKey.CREATORS_CULT)


async def test_interstellar_traveller_needs_an_arrived_journey(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    other = await add_world(session, "Kesh")
    route = await _route(session, world.world.id, other.id)
    traveller = await make_entity(session, "Wayfarers", EntityType.PEOPLE, world_id=world.world.id)
    journey = JourneyRow(
        traveller_entity_id=traveller.id,
        route_id=route.id,
        origin_world_id=world.world.id,
        destination_world_id=other.id,
        intent=JourneyIntent.EXPLORATION,
        epochs_left=1,
        start_epoch=1,
    )
    session.add(journey)
    await session.flush()
    assert not await _reached(session, rules, AchievementKey.INTERSTELLAR_TRAVELLER)
    journey.status = JourneyStatus.ARRIVED
    await session.flush()
    assert await _reached(session, rules, AchievementKey.INTERSTELLAR_TRAVELLER)


async def test_saga_completed_needs_a_completed_legendary_quest(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    thread = ThreadRow(epoch=1, text="The long road")
    session.add(thread)
    await session.flush()
    quest = LegendaryQuestRow(thread_id=thread.id, kind=LegendaryQuestKind.ARCHIVE, opened_by=ActorKind.SON, opened_epoch=1, deadline_epoch=9)
    session.add(quest)
    await session.flush()
    assert not await _reached(session, rules, AchievementKey.SAGA_COMPLETED)
    quest.outcome = LegendaryQuestOutcome.COMPLETED
    await session.flush()
    assert await _reached(session, rules, AchievementKey.SAGA_COMPLETED)


async def test_epoch_milestones(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    first, ancient = rules.goals.ach_epochs, rules.goals.ach_ancient_epochs
    assert not await _reached(session, rules, AchievementKey.GOD_OF_EPOCHS, first - 1)
    assert await _reached(session, rules, AchievementKey.GOD_OF_EPOCHS, first)
    assert not await _reached(session, rules, AchievementKey.ANCIENT, ancient - 1)
    assert await _reached(session, rules, AchievementKey.ANCIENT, ancient)


async def test_crowded_pantheon_counts_living_sons(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _goals(rules, ach_sons=2)
    await make_son(session, "Velkar", world.world.id)
    assert not await _reached(session, tuned, AchievementKey.CROWDED_PANTHEON)
    await make_son(session, "Iolen", world.world.id)
    assert await _reached(session, tuned, AchievementKey.CROWDED_PANTHEON)


async def test_first_explorers_needs_a_discovery_bond(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    explorer = await make_entity(session, "Asha", EntityType.MORTAL, world_id=world.world.id)
    land = await make_entity(session, "Far Vale", EntityType.REGION, world_id=world.world.id)
    assert not await _reached(session, rules, AchievementKey.FIRST_EXPLORERS)
    await bond(session, explorer.id, land.id, BondKind.DISCOVERED)
    assert await _reached(session, rules, AchievementKey.FIRST_EXPLORERS)


async def test_sensed_world_needs_a_born_intuition(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    mortal = await make_entity(session, "Asha", EntityType.MORTAL, world_id=world.world.id)
    intuition = HorizonIntuitionRow(mortal_entity_id=mortal.id, epoch=1)
    session.add(intuition)
    await session.flush()
    assert not await _reached(session, rules, AchievementKey.SENSED_WORLD)
    intuition.status = HorizonStatus.BORN
    await session.flush()
    assert await _reached(session, rules, AchievementKey.SENSED_WORLD)


async def test_weapons_silent_is_earned_when_enough_peoples_live_without_war(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _goals(rules, ach_peace_min_peoples=2)
    await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id)
    assert not await _reached(session, tuned, AchievementKey.WEAPONS_SILENT)
    await make_entity(session, "Saltfolk", EntityType.PEOPLE, world_id=world.world.id)
    assert await _reached(session, tuned, AchievementKey.WEAPONS_SILENT)


async def test_evaluation_persists_each_earned_achievement_once(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    await add_world(session, "Kesh")
    first = await evaluate_goals(make_context(session, rules, 3, "goals"))
    assert AchievementKey.SECOND_SKY in first.earned
    second = await evaluate_goals(make_context(session, rules, 4, "goals"))
    assert AchievementKey.SECOND_SKY not in second.earned


async def test_one_faith_measure(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _goals(rules, one_faith_min_peoples=2)
    son = await make_son(session, "Velkar", world.world.id)
    other = await make_son(session, "Iolen", world.world.id)
    first = await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id)
    second = await make_entity(session, "Saltfolk", EntityType.PEOPLE, world_id=world.world.id)
    await bond(session, first.id, son.id, BondKind.WORSHIPS)
    await bond(session, second.id, other.id, BondKind.WORSHIPS)
    await start_scenario(session, tuned, ScenarioKey.ONE_FAITH)
    row = await session.get(ScenarioRow, 1)
    assert row is not None
    divided = await measure(session, tuned, row, 3)
    assert not divided.done and divided.percent == 50
    third = await make_entity(session, "Windfolk", EntityType.PEOPLE, world_id=world.world.id)
    await bond(session, third.id, son.id, BondKind.WORSHIPS)
    still = await measure(session, tuned, row, 3)
    assert not still.done
    await bond(session, second.id, son.id, BondKind.WORSHIPS)
    await BondRepository(session).close_between(second.id, other.id, [BondKind.WORSHIPS], 2)
    united = await measure(session, tuned, row, 3)
    assert united.done and united.percent == 100


async def test_lost_star_needs_a_star_reborn_after_the_start(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    await start_scenario(session, rules, ScenarioKey.LOST_STAR)
    row = await session.get(ScenarioRow, 1)
    assert row is not None and row.baseline_count == 0
    nothing = await measure(session, rules, row, 3)
    assert not nothing.done and "no dead star" in nothing.text
    await _star(session, "Embers", StarType.DEAD_STAR)
    waiting = await measure(session, rules, row, 3)
    assert not waiting.done and "1 dead stars" in waiting.text
    await _star(session, "Phoenix", StarType.REBORN_STAR)
    reborn = await measure(session, rules, row, 4)
    assert reborn.done and reborn.percent == 100


async def test_lost_star_ignores_stars_reborn_before_the_start(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    await _star(session, "Phoenix", StarType.REBORN_STAR)
    await start_scenario(session, rules, ScenarioKey.LOST_STAR)
    row = await session.get(ScenarioRow, 1)
    assert row is not None and row.baseline_count == 1
    assert not (await measure(session, rules, row, 3)).done


async def test_many_worlds_counts_inhabited_worlds(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _goals(rules, inhabited_worlds=2)
    await start_scenario(session, tuned, ScenarioKey.MANY_WORLDS)
    row = await session.get(ScenarioRow, 1)
    assert row is not None
    await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id)
    half = await measure(session, tuned, row, 3)
    assert not half.done and half.percent == 50
    other = await add_world(session, "Kesh")
    await make_entity(session, "Keshfolk", EntityType.PEOPLE, world_id=other.id)
    assert (await measure(session, tuned, row, 3)).done


async def test_cosmic_power_needs_the_target_tier(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _goals(rules, cosmic_stage=3)
    await start_scenario(session, tuned, ScenarioKey.COSMIC_POWER)
    row = await session.get(ScenarioRow, 1)
    assert row is not None
    people = await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id)
    people.civ_tier = 1
    await session.flush()
    partial = await measure(session, tuned, row, 3)
    assert not partial.done and partial.percent == 33
    people.civ_tier = 3
    await session.flush()
    assert (await measure(session, tuned, row, 3)).done


async def test_a_failing_measure_reports_text_instead_of_crashing(
    session: AsyncSession, world: GodsWorld, rules: Rules, monkeypatch: pytest.MonkeyPatch
) -> None:
    await start_scenario(session, rules, ScenarioKey.COSMIC_POWER)
    row = await session.get(ScenarioRow, 1)
    assert row is not None

    async def broken(*args: object) -> None:
        raise ValueError("no ledger")

    monkeypatch.setitem(goals_module.MEASURES, ScenarioKey.COSMIC_POWER, broken)
    progress = await safe_measure(session, rules, row, 3)
    assert progress.percent == 0 and not progress.done and "could not be measured: no ledger" in progress.text
    result = await evaluate_goals(make_context(session, rules, 3, "goals"))
    assert result.completed == () and row.status is ScenarioStatus.RUNNING
