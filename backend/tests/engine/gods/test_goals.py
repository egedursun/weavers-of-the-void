import math
from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.achievements import ACHIEVEMENTS
from aerona.catalog.scenarios import SCENARIOS, roman
from aerona.core.errors import ConflictError, NotFoundError, ValidationFailedError
from aerona.db.tables.meta import AchievementRow, NotificationRow, ScenarioRow, ScoreRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.meta import AchievementKey, GoalBasis, GoalComparator, GoalMetric, ScenarioKey, ScenarioStatus, ScoreComponent
from aerona.domain.enums.son import SonDeathCause
from aerona.engine.gods.goals import custom_points, epoch_end_goals, evaluate_goals, preset_points, score
from aerona.engine.gods.god_death import god_death, resurrect_son
from aerona.engine.gods.power import declare_rebellion
from aerona.engine.phases.goals import goals
from aerona.rules.registry import Rules
from aerona.services.gods.goals import (
    abandon_scenario,
    delete_scenario,
    edit_scenario,
    evaluate_now,
    goals_overview,
    hold_scenario,
    quote_goal,
    start_custom,
    start_scenario,
)
from tests.engine.gods.factories import GodsWorld, add_world, chronicle_keys, make_context, make_entity, make_son


def _goals(rules: Rules, **changes: int) -> Rules:
    return replace(rules, goals=replace(rules.goals, **changes))


async def _only(session: AsyncSession) -> ScenarioRow:
    row = await session.scalar(select(ScenarioRow).order_by(ScenarioRow.id.desc()))
    assert row is not None
    return row


def test_catalogs_cover_every_key(rules: Rules) -> None:
    assert set(SCENARIOS) == set(ScenarioKey)
    assert set(ACHIEVEMENTS) == set(AchievementKey)
    assert roman(1) == "I" and roman(4) == "IV" and roman(14) == "XIV"
    spec = SCENARIOS[ScenarioKey.LONG_PEACE]
    assert spec.name(spec.target_for_tier(rules, 2), 2).endswith(" II")
    assert spec.target_for_tier(rules, 3) == rules.goals.peace_epochs + 2 * rules.goals.peace_step
    for key, item in SCENARIOS.items():
        assert "{" not in item.description(rules, item.default_target(rules)), key


async def test_score_breakdown_reads_every_part(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id)
    await make_entity(session, "Kin of the Reeds", EntityType.SPECIES, world_id=world.world.id)
    await make_entity(session, "The Counting", EntityType.KNOWLEDGE, world_id=world.world.id)
    world.cosmos.doom_clock = 50
    breakdown = await score(session, rules, 3)
    goals_rules = rules.goals
    assert set(breakdown.parts) == set(ScoreComponent)
    assert breakdown.parts[ScoreComponent.POPULATION] == round(math.log10(6001) * goals_rules.score_population)
    assert breakdown.parts[ScoreComponent.DIVERSITY] == 4
    assert breakdown.parts[ScoreComponent.WORLDS] == goals_rules.score_world
    assert breakdown.parts[ScoreComponent.LIFE] == goals_rules.score_life
    assert breakdown.parts[ScoreComponent.KNOWLEDGE] == goals_rules.score_knowledge
    assert breakdown.parts[ScoreComponent.DOOMSDAY] == -round(50 / rules.balance.apocalypse_threshold * goals_rules.score_apocalypse_penalty)


async def test_score_parts_stop_at_their_caps(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _goals(rules, score_life=100, score_life_cap=150)
    await make_entity(session, "Kin of the Reeds", EntityType.SPECIES, world_id=world.world.id)
    await make_entity(session, "Kin of the Stones", EntityType.SPECIES, world_id=world.world.id)
    assert (await score(session, tuned, 3)).parts[ScoreComponent.LIFE] == 150


async def test_a_repeated_goal_earns_only_what_it_adds_over_the_best_before(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _goals(rules, peace_epochs=1, peace_step=1)
    await start_scenario(session, tuned, ScenarioKey.LONG_PEACE)
    with pytest.raises(ConflictError):
        await start_scenario(session, tuned, ScenarioKey.LONG_PEACE)
    result = await epoch_end_goals(make_context(session, tuned, 3, "goals"))
    assert result.completed == (ScenarioKey.LONG_PEACE,)
    first_points = preset_points(tuned, ScenarioKey.LONG_PEACE, 1, None)
    assert result.score.parts[ScoreComponent.SCENARIOS] == first_points
    overview = await goals_overview(session, tuned)
    peace = next(view for view in overview.scenarios if view.key is ScenarioKey.LONG_PEACE)
    assert peace.next_tier == 2 and peace.default_target == 2
    await start_scenario(session, tuned, ScenarioKey.LONG_PEACE, target=1)
    again = await epoch_end_goals(make_context(session, tuned, 4, "goals"))
    assert again.score.parts[ScoreComponent.SCENARIOS] == first_points
    await start_scenario(session, tuned, ScenarioKey.LONG_PEACE)
    await epoch_end_goals(make_context(session, tuned, 5, "goals"))
    await epoch_end_goals(make_context(session, tuned, 6, "goals"))
    third = await epoch_end_goals(make_context(session, tuned, 7, "goals"))
    rows = list(await session.scalars(select(ScenarioRow).order_by(ScenarioRow.id)))
    assert [row.tier for row in rows] == [1, 2, 3]
    assert [row.awarded_points for row in rows] == [first_points, 0, rows[2].points - first_points]
    assert third.score.parts[ScoreComponent.SCENARIOS] == rows[2].points
    assert "gods.goals.achieved" in await chronicle_keys(session)
    assert await session.get(ScoreRow, 7) is not None


async def test_manual_evaluation_does_not_advance_the_peace_counter(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    await start_scenario(session, rules, ScenarioKey.LONG_PEACE)
    await evaluate_now(session, rules)
    await evaluate_now(session, rules)
    row = await _only(session)
    assert row.counter == 0
    await epoch_end_goals(make_context(session, rules, 3, "goals"))
    await session.refresh(row)
    assert row.counter == 1


async def test_a_deadline_fails_the_goal_at_the_end_of_its_epoch(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    await start_scenario(session, rules, ScenarioKey.MANY_WORLDS, target=3, deadline_epochs=2)
    row = await _only(session)
    assert row.deadline_epoch == world.cosmos.epoch + 2
    assert row.points == preset_points(rules, ScenarioKey.MANY_WORLDS, 3, row.deadline_epoch) > preset_points(rules, ScenarioKey.MANY_WORLDS, 3, None)
    early = await evaluate_goals(make_context(session, rules, row.deadline_epoch, "goals"))
    assert early.failed == () and row.status is ScenarioStatus.RUNNING
    late = await epoch_end_goals(make_context(session, rules, row.deadline_epoch, "goals"))
    assert late.failed == (ScenarioKey.MANY_WORLDS,)
    assert row.result is not None and f"deadline of epoch {row.deadline_epoch}" in row.result


async def test_a_held_goal_waits_and_its_deadline_moves_with_it(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _goals(rules, peace_epochs=1)
    await start_scenario(session, tuned, ScenarioKey.LONG_PEACE, deadline_epochs=1)
    row = await _only(session)
    deadline = row.deadline_epoch
    await hold_scenario(session, tuned, row.id, held=True)
    result = await epoch_end_goals(make_context(session, tuned, 3, "goals"))
    assert result.completed == () and result.failed == ()
    assert row.counter == 0 and row.deadline_epoch == (deadline or 0) + 1
    await hold_scenario(session, tuned, row.id, held=False)
    released = await epoch_end_goals(make_context(session, tuned, 3, "goals"))
    assert released.completed == (ScenarioKey.LONG_PEACE,)


async def test_doom_scenario_fails(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    await start_scenario(session, rules, ScenarioKey.DOOM_FAR)
    world.cosmos.doom_clock = rules.balance.apocalypse_threshold
    result = await evaluate_goals(make_context(session, rules, 3, "goals"))
    assert result.failed == (ScenarioKey.DOOM_FAR,)
    assert "gods.goals.lost" in await chronicle_keys(session)


async def test_loyal_pantheon_fails_on_new_rebellion(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    await start_scenario(session, rules, ScenarioKey.LOYAL_PANTHEON)
    await declare_rebellion(make_context(session, rules, 2), world.creator, son, "enough", spontaneous=False)
    result = await evaluate_goals(make_context(session, rules, 3, "goals"))
    assert result.failed == (ScenarioKey.LOYAL_PANTHEON,)


async def test_new_horizons_progress(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _goals(rules, horizon_regions=1)
    await start_scenario(session, tuned, ScenarioKey.NEW_HORIZONS, target=2)
    await make_entity(session, "New Vale", EntityType.REGION, world_id=world.world.id)
    overview = await goals_overview(session, tuned)
    assert overview.running[0].progress.percent == 50
    await make_entity(session, "New Cave", EntityType.PLACE, world_id=world.world.id, location_id=world.region.id)
    result = await evaluate_goals(make_context(session, tuned, 3, "goals"))
    assert result.completed == (ScenarioKey.NEW_HORIZONS,)


async def test_gained_presets_count_from_the_start(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    await make_entity(session, "Kin of the Reeds", EntityType.SPECIES, world_id=world.world.id)
    await start_scenario(session, rules, ScenarioKey.TEEMING_LIFE, target=2)
    row = await _only(session)
    assert row.baseline_value == 1
    await make_entity(session, "Kin of the Stones", EntityType.SPECIES, world_id=world.world.id)
    half = await goals_overview(session, rules)
    assert half.running[0].progress.percent == 50 and half.running[0].progress.value == 1
    await make_entity(session, "Kin of the Sands", EntityType.SPECIES, world_id=world.world.id)
    result = await evaluate_goals(make_context(session, rules, 3, "goals"))
    assert result.completed == (ScenarioKey.TEEMING_LIFE,)


async def test_a_custom_goal_reaches_any_metric(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    await start_custom(session, rules, metric=GoalMetric.LANGUAGES, comparator=GoalComparator.AT_LEAST, basis=GoalBasis.TOTAL, target=2, title="Two tongues")
    row = await _only(session)
    assert row.key is ScenarioKey.CUSTOM and row.baseline_value == 0
    assert row.points == custom_points(rules, comparator=GoalComparator.AT_LEAST, basis=GoalBasis.TOTAL, start=0, target=2, hold_epochs=0, deadline_epoch=None)
    await make_entity(session, "Old Tongue", EntityType.LANGUAGE, world_id=world.world.id)
    overview = await goals_overview(session, rules)
    running = overview.running[0]
    assert running.name == "Two tongues" and running.progress.percent == 50 and running.metric is GoalMetric.LANGUAGES
    await make_entity(session, "New Tongue", EntityType.LANGUAGE, world_id=world.world.id)
    result = await evaluate_goals(make_context(session, rules, 3, "goals"))
    assert result.completed == (ScenarioKey.CUSTOM,)
    assert row.awarded_points == row.points


async def test_a_custom_goal_with_a_hold_must_stay_reached(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    await start_custom(session, rules, metric=GoalMetric.ONGOING_WARS, comparator=GoalComparator.AT_MOST, basis=GoalBasis.TOTAL, target=0, hold_epochs=2)
    row = await _only(session)
    assert row.points == 2 * rules.goals.custom_hold_points
    first = await epoch_end_goals(make_context(session, rules, 3, "goals"))
    assert first.completed == () and row.counter == 1
    second = await epoch_end_goals(make_context(session, rules, 4, "goals"))
    assert second.completed == (ScenarioKey.CUSTOM,)


async def test_custom_goals_run_side_by_side_up_to_the_limit(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _goals(rules, custom_max_running=2)
    for target in (3, 4):
        await start_custom(session, tuned, metric=GoalMetric.WORLDS, comparator=GoalComparator.AT_LEAST, basis=GoalBasis.TOTAL, target=target)
    with pytest.raises(ConflictError):
        await start_custom(session, tuned, metric=GoalMetric.WORLDS, comparator=GoalComparator.AT_LEAST, basis=GoalBasis.TOTAL, target=5)
    with pytest.raises(ValidationFailedError):
        await start_custom(session, rules, metric=GoalMetric.WORLDS, comparator=GoalComparator.AT_MOST, basis=GoalBasis.GAINED, target=5)
    with pytest.raises(ValidationFailedError):
        await start_scenario(session, rules, ScenarioKey.COSMIC_POWER, target=99)


def test_custom_points_reward_distance_holds_and_deadlines(rules: Rules) -> None:
    goals_rules = rules.goals
    reached = custom_points(rules, comparator=GoalComparator.AT_LEAST, basis=GoalBasis.TOTAL, start=10, target=10, hold_epochs=0, deadline_epoch=None)
    doubled = custom_points(rules, comparator=GoalComparator.AT_LEAST, basis=GoalBasis.TOTAL, start=10, target=20, hold_epochs=0, deadline_epoch=None)
    far = custom_points(rules, comparator=GoalComparator.AT_LEAST, basis=GoalBasis.TOTAL, start=1, target=1000, hold_epochs=0, deadline_epoch=None)
    held = custom_points(rules, comparator=GoalComparator.AT_LEAST, basis=GoalBasis.TOTAL, start=10, target=20, hold_epochs=3, deadline_epoch=None)
    timed = custom_points(rules, comparator=GoalComparator.AT_LEAST, basis=GoalBasis.TOTAL, start=10, target=20, hold_epochs=0, deadline_epoch=9)
    halved = custom_points(rules, comparator=GoalComparator.AT_MOST, basis=GoalBasis.TOTAL, start=20, target=10, hold_epochs=0, deadline_epoch=None)
    assert reached == 0
    assert doubled == goals_rules.custom_points == halved
    assert far == round(goals_rules.custom_points * goals_rules.custom_ratio_cap_pct / 100)
    assert held == doubled + 3 * goals_rules.custom_hold_points
    assert timed == round(doubled * (100 + goals_rules.deadline_bonus_pct) / 100)


async def test_editing_a_goal_reprices_it_and_deleting_strikes_its_points(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    await start_scenario(session, rules, ScenarioKey.MANY_WORLDS, target=2)
    row = await _only(session)
    small = row.points
    await edit_scenario(session, rules, row.id, target=4, deadline_epochs=3)
    assert row.target == 4 and row.deadline_epoch == world.cosmos.epoch + 3 and row.points > small
    await edit_scenario(session, rules, row.id, target=1, deadline_epochs=None)
    assert row.deadline_epoch is None
    await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id)
    result = await evaluate_goals(make_context(session, rules, 3, "goals"))
    assert result.score.parts[ScoreComponent.SCENARIOS] == row.awarded_points > 0
    after = await delete_scenario(session, rules, row.id)
    assert after.score.parts[ScoreComponent.SCENARIOS] == 0
    with pytest.raises(NotFoundError):
        await delete_scenario(session, rules, row.id)


async def test_a_quote_names_the_points_a_start_will_fix(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    quote = await quote_goal(session, rules, ScenarioKey.AGE_OF_WONDERS, target=4, deadline_epochs=6)
    await start_scenario(session, rules, ScenarioKey.AGE_OF_WONDERS, target=4, deadline_epochs=6)
    assert quote.points == (await _only(session)).points and quote.target == 4
    custom = await quote_goal(session, rules, ScenarioKey.CUSTOM, metric=GoalMetric.STARS, comparator=GoalComparator.AT_LEAST, basis=GoalBasis.GAINED, target=3)
    await start_custom(session, rules, metric=GoalMetric.STARS, comparator=GoalComparator.AT_LEAST, basis=GoalBasis.GAINED, target=3)
    assert custom.points == (await _only(session)).points and custom.name == "Gain 3 stars"


async def test_return_from_death_only_on_resurrection(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    ctx = make_context(session, rules, 3)
    await god_death(ctx, son, "fell", SonDeathCause.OTHER)
    first = await evaluate_goals(make_context(session, rules, 3, "goals"))
    assert (AchievementKey.RETURN_FROM_DEATH, 1) not in first.earned
    await resurrect_son(ctx, son, "test")
    await goals(make_context(session, rules, 4, "goals"))
    earned = set(await session.scalars(select(AchievementRow.key)))
    assert AchievementKey.RETURN_FROM_DEATH in earned
    assert AchievementKey.WEAPONS_SILENT not in earned
    assert list(await session.scalars(select(NotificationRow)))


async def test_abandon_scenario(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    overview = await start_scenario(session, rules, ScenarioKey.ONE_FAITH)
    scenario_id = overview.running[0].id
    after = await abandon_scenario(session, rules, scenario_id)
    assert not after.running
    faith = next(view for view in after.scenarios if view.key is ScenarioKey.ONE_FAITH)
    assert faith.history[0].status is ScenarioStatus.ABANDONED
    with pytest.raises(NotFoundError):
        await abandon_scenario(session, rules, scenario_id)


async def test_the_overview_shows_every_metric_and_achievement_progress(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    await add_world(session, "Kesh")
    overview = await goals_overview(session, rules)
    assert {view.metric for view in overview.metrics} == set(GoalMetric)
    assert len(overview.achievements) == len(AchievementKey) and len(overview.categories) == len({spec.category for spec in ACHIEVEMENTS.values()})
    sky = next(view for view in overview.achievements if view.key is AchievementKey.SECOND_SKY)
    assert sky.value == 2 and sky.tier == 0 and sky.percent == 100
    await evaluate_now(session, rules)
    earned = next(view for view in (await goals_overview(session, rules)).achievements if view.key is AchievementKey.SECOND_SKY)
    assert earned.tier == 1 and earned.tiers[0].epoch is not None and 0 <= earned.percent < 100
