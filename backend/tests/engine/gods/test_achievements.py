import re
from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.achievements import ACHIEVEMENTS
from aerona.catalog.goal_metrics import METRICS
from aerona.catalog.scenarios import SCENARIOS
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.worlds import StarDraft, WorldRepository
from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.entities import EntityFlagRow
from aerona.db.tables.lore import LegendaryQuestRow, MessageRow, ThreadRow
from aerona.db.tables.meta import AchievementRow, NotificationRow, ScenarioRow
from aerona.db.tables.routes import HorizonIntuitionRow, JourneyRow, RouteRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import LegendaryQuestOutcome
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.meta import ACHIEVEMENT_TIERS, AchievementKey, GoalMetric, ScenarioKey, ScenarioStatus, ScoreComponent
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.quests import QuestAim, QuestTargetKind
from aerona.domain.enums.travel import HorizonStatus, JourneyIntent, JourneyStatus, TravelMethod
from aerona.domain.enums.world import StarType
from aerona.domain.models.entity_stats import StructureStats
from aerona.engine.gods import goals as goals_module
from aerona.engine.gods.goals import evaluate_goals, measure, safe_measure
from aerona.engine.gods.metrics import MEASURES, measure_metric
from aerona.rules.registry import Rules
from aerona.services.gods.goals import start_scenario
from tests.engine.gods.factories import GodsWorld, add_world, bond, make_context, make_entity, make_son


def _goals(rules: Rules, **changes: int) -> Rules:
    return replace(rules, goals=replace(rules.goals, **changes))


def _achievements(rules: Rules, **changes: int) -> Rules:
    return replace(rules, achievements=replace(rules.achievements, **changes))


async def _reached(session: AsyncSession, rules: Rules, key: AchievementKey, epoch: int = 3, tier: int = 1) -> bool:
    spec = ACHIEVEMENTS[key]
    return await measure_metric(session, rules, spec.metric, epoch) >= spec.threshold(rules, tier)


async def _star(session: AsyncSession, name: str, star_type: StarType) -> None:
    await WorldRepository(session).create_star(StarDraft(name, star_type, 50, 1.0, 1.0, 1))


async def _route(session: AsyncSession, first_id: int, second_id: int) -> RouteRow:
    route = RouteRow(world_a_id=first_id, world_b_id=second_id, method=TravelMethod.LIGHT_SAIL, duration_epochs=2, danger=10, created_epoch=1)
    session.add(route)
    await session.flush()
    return route


def test_every_achievement_rests_on_a_measured_metric_with_three_rising_tiers(rules: Rules) -> None:
    assert set(ACHIEVEMENTS) == set(AchievementKey)
    assert set(MEASURES) == set(GoalMetric) == set(METRICS)
    for key, spec in ACHIEVEMENTS.items():
        thresholds = [spec.threshold(rules, tier) for tier in ACHIEVEMENT_TIERS]
        assert thresholds == sorted(set(thresholds)), key
        assert [spec.points(rules, tier) for tier in ACHIEVEMENT_TIERS] == sorted(spec.points(rules, tier) for tier in ACHIEVEMENT_TIERS), key
        for tier in ACHIEVEMENT_TIERS:
            assert "{" not in spec.description(rules, tier) and spec.name(tier).startswith(spec.title), key
    assert ACHIEVEMENTS[AchievementKey.SECOND_SKY].name(2) == "Many skies II"


async def test_every_metric_measures_a_count_on_a_small_world(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    for metric in GoalMetric:
        assert await measure_metric(session, rules, metric, 3) >= 0, metric


async def test_second_sky_needs_the_threshold_of_worlds(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    assert not await _reached(session, rules, AchievementKey.SECOND_SKY)
    await add_world(session, "Kesh")
    assert await _reached(session, rules, AchievementKey.SECOND_SKY)


async def test_constellation_needs_the_threshold_of_stars(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _achievements(rules, tier_1_constellation=3)
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


async def test_creators_hand_counts_only_a_successful_suppression(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    session.add(ActionRecordRow(epoch=2, actor_kind=ActorKind.CREATOR, actor_node_id=world.creator.id, kind=ActionKind.SUPPRESS_FAILED))
    await session.flush()
    assert not await _reached(session, rules, AchievementKey.CREATORS_HAND)
    session.add(ActionRecordRow(epoch=2, actor_kind=ActorKind.CREATOR, actor_node_id=world.creator.id, kind=ActionKind.SUPPRESS_REBELLION))
    await session.flush()
    assert await _reached(session, rules, AchievementKey.CREATORS_HAND)


async def test_babel_needs_the_threshold_of_languages(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _achievements(rules, tier_1_babel=2)
    await make_entity(session, "Old Tongue", EntityType.LANGUAGE, world_id=world.world.id)
    assert not await _reached(session, tuned, AchievementKey.BABEL)
    await make_entity(session, "New Tongue", EntityType.LANGUAGE, world_id=world.world.id)
    assert await _reached(session, tuned, AchievementKey.BABEL)


async def test_crowded_world_needs_the_total_population(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id)
    assert not await _reached(session, _achievements(rules, tier_1_crowded_world=6001), AchievementKey.CROWDED_WORLD)
    assert await _reached(session, _achievements(rules, tier_1_crowded_world=6000), AchievementKey.CROWDED_WORLD)


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
    tuned = _achievements(rules, tier_1_creators_cult=2)
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
    quest = LegendaryQuestRow(
        thread_id=thread.id, aim=QuestAim.FIND, target_kind=QuestTargetKind.KNOWLEDGE, locked=[], opened_by=ActorKind.SON, opened_epoch=1, deadline_epoch=9
    )
    session.add(quest)
    await session.flush()
    assert not await _reached(session, rules, AchievementKey.SAGA_COMPLETED)
    quest.outcome = LegendaryQuestOutcome.COMPLETED
    await session.flush()
    assert await _reached(session, rules, AchievementKey.SAGA_COMPLETED)


async def test_epoch_milestones(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    first, ancient = rules.achievements.tier_1_god_of_epochs, rules.achievements.tier_1_ancient
    assert not await _reached(session, rules, AchievementKey.GOD_OF_EPOCHS, first - 1)
    assert await _reached(session, rules, AchievementKey.GOD_OF_EPOCHS, first)
    assert not await _reached(session, rules, AchievementKey.ANCIENT, ancient - 1)
    assert await _reached(session, rules, AchievementKey.ANCIENT, ancient)


async def test_crowded_pantheon_counts_living_sons(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _achievements(rules, tier_1_crowded_pantheon=2)
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
    tuned = _achievements(rules, tier_1_weapons_silent=2)
    await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id)
    assert not await _reached(session, tuned, AchievementKey.WEAPONS_SILENT)
    await make_entity(session, "Saltfolk", EntityType.PEOPLE, world_id=world.world.id)
    assert await _reached(session, tuned, AchievementKey.WEAPONS_SILENT)


async def test_evaluation_persists_each_earned_achievement_once(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    await add_world(session, "Kesh")
    first = await evaluate_goals(make_context(session, rules, 3, "goals"))
    assert (AchievementKey.SECOND_SKY, 1) in first.earned
    second = await evaluate_goals(make_context(session, rules, 4, "goals"))
    assert (AchievementKey.SECOND_SKY, 1) not in second.earned


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
    assert row is not None and row.baseline_value == 0
    nothing = await measure(session, rules, row, 3)
    assert not nothing.done and "no dead star" in nothing.text
    await _star(session, "Embers", StarType.DEAD_STAR)
    waiting = await measure(session, rules, row, 3)
    assert not waiting.done and waiting.percent == 0 and "1 dead star is waiting" in waiting.text
    await _star(session, "Phoenix", StarType.REBORN_STAR)
    reborn = await measure(session, rules, row, 4)
    assert reborn.done and reborn.percent == 100


async def test_lost_star_ignores_stars_reborn_before_the_start(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    await _star(session, "Phoenix", StarType.REBORN_STAR)
    await start_scenario(session, rules, ScenarioKey.LOST_STAR)
    row = await session.get(ScenarioRow, 1)
    assert row is not None and row.baseline_value == 1
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


async def test_tiers_are_earned_in_order_and_each_is_announced(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _achievements(rules, tier_1_second_sky=2, tier_2_second_sky=3, tier_3_second_sky=4)
    await add_world(session, "Kesh")
    await add_world(session, "Tamar")
    first = await evaluate_goals(make_context(session, tuned, 3, "goals"))
    assert {(AchievementKey.SECOND_SKY, 1), (AchievementKey.SECOND_SKY, 2)} <= set(first.earned)
    assert (AchievementKey.SECOND_SKY, 3) not in first.earned
    await add_world(session, "Ulm")
    second = await evaluate_goals(make_context(session, tuned, 4, "goals"))
    assert (AchievementKey.SECOND_SKY, 3) in second.earned
    tiers = list(await session.scalars(select(AchievementRow.tier).where(AchievementRow.key == AchievementKey.SECOND_SKY).order_by(AchievementRow.tier)))
    assert tiers == [1, 2, 3]
    titles = set(await session.scalars(select(NotificationRow.title)))
    assert any("Many skies III" in title for title in titles)
    assert second.score.parts[ScoreComponent.ACHIEVEMENTS] >= sum(ACHIEVEMENTS[AchievementKey.SECOND_SKY].points(tuned, tier) for tier in ACHIEVEMENT_TIERS)


async def test_wonders_count_engine_wonders_and_flagged_works(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    stats = StructureStats()
    await make_entity(
        session, "The Spire", EntityType.STRUCTURE, world_id=world.world.id, location_id=world.region.id, stats=stats, engine_kind=EngineKind.WONDER
    )
    flagged = await make_entity(session, "The Hall", EntityType.STRUCTURE, world_id=world.world.id, location_id=world.region.id, stats=stats)
    assert await measure_metric(session, rules, GoalMetric.WONDERS, 3) == 1
    session.add(EntityFlagRow(entity_id=flagged.id, flag=EntityFlag.WONDER, epoch=2))
    await session.flush()
    assert await measure_metric(session, rules, GoalMetric.WONDERS, 3) == 2


async def test_flag_metrics_count_only_living_records(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    realm = await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id)
    session.add(EntityFlagRow(entity_id=realm.id, flag=EntityFlag.EMPIRE, epoch=2))
    session.add(EntityFlagRow(entity_id=realm.id, flag=EntityFlag.GOLDEN_AGE, epoch=2))
    await session.flush()
    assert await measure_metric(session, rules, GoalMetric.EMPIRES, 3) == 1
    assert await measure_metric(session, rules, GoalMetric.GOLDEN_AGES, 3) == 1
    realm.status = EntityStatus.DEAD
    realm.end_epoch = 3
    await session.flush()
    assert await measure_metric(session, rules, GoalMetric.EMPIRES, 3) == 0


async def test_creator_metrics_read_the_creators_own_deeds(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    for kind in (ActionKind.SUPPRESS_REBELLION, ActionKind.SUPPRESS_REBELLION, ActionKind.EVALUATE_GOALS):
        session.add(ActionRecordRow(epoch=2, actor_kind=ActorKind.CREATOR, actor_node_id=world.creator.id, kind=kind))
    session.add(ActionRecordRow(epoch=2, actor_kind=ActorKind.SON, kind=ActionKind.OTHER))
    await session.flush()
    assert await measure_metric(session, rules, GoalMetric.CREATOR_DEEDS, 3) == 3
    assert await measure_metric(session, rules, GoalMetric.LEVERS_USED, 3) == 2


async def test_doom_percent_and_epoch_metrics(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    world.cosmos.doom_clock = rules.balance.apocalypse_threshold // 2
    assert await measure_metric(session, rules, GoalMetric.DOOM_PERCENT, 3) == 50
    assert await measure_metric(session, rules, GoalMetric.EPOCH, 7) == 7


def test_achievements_and_goals_read_apart_from_each_other(rules: Rules) -> None:
    titles = [spec.title for spec in ACHIEVEMENTS.values()]
    assert len(titles) == len(set(titles))
    descriptions = [spec.description(rules, 1) for spec in ACHIEVEMENTS.values()]
    assert len(descriptions) == len(set(descriptions))
    labels = [spec.label for spec in METRICS.values()]
    assert len(labels) == len(set(labels))


def test_goal_texts_carry_no_gendered_default(rules: Rules) -> None:
    gendered = re.compile(r"\b(father|fathers|brother|brothers|he|his|him|himself|mother|sister)\b", re.IGNORECASE)
    texts = [key.value.replace("_", " ") for key in (*AchievementKey, *ScenarioKey, *GoalMetric)]
    texts += [spec.name(tier) + " " + spec.description(rules, tier) for spec in ACHIEVEMENTS.values() for tier in ACHIEVEMENT_TIERS]
    texts += [spec.name(spec.default_target(rules)) + " " + spec.description(rules, spec.default_target(rules)) for spec in SCENARIOS.values()]
    texts += [spec.label for spec in METRICS.values()]
    assert [text for text in texts if gendered.search(text)] == []
