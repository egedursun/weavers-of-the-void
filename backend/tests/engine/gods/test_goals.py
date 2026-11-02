import math
from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog import god_lines
from aerona.catalog.achievements import ACHIEVEMENTS, ordinal_word
from aerona.catalog.scenarios import SCENARIOS
from aerona.core.errors import ConflictError, NotFoundError
from aerona.db.tables.meta import AchievementRow, NotificationRow, ScenarioRow, ScoreRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.meta import AchievementKey, ScenarioKey, ScenarioStatus, ScoreComponent
from aerona.domain.enums.son import SonDeathCause
from aerona.engine.gods.goals import epoch_end_goals, evaluate_goals, score
from aerona.engine.gods.god_death import god_death, resurrect_son
from aerona.engine.gods.power import declare_rebellion
from aerona.engine.phases.goals import goals
from aerona.rules.registry import Rules
from aerona.services.gods.goals import abandon_scenario, evaluate_now, goals_overview, start_scenario
from tests.engine.gods.factories import GodsWorld, chronicle_keys, make_context, make_entity, make_son


def test_catalogs_cover_every_key(rules: Rules) -> None:
    assert set(SCENARIOS) == set(ScenarioKey)
    assert set(ACHIEVEMENTS) == set(AchievementKey)
    assert ACHIEVEMENTS[AchievementKey.SECOND_SKY].name(rules) == "Second sky"
    assert ordinal_word(12) == "12th" and ordinal_word(22) == "22nd"


async def test_score_breakdown(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id)
    world.cosmos.doom_clock = 50
    breakdown = await score(session, rules)
    goals_rules = rules.goals
    assert breakdown.parts[ScoreComponent.POPULATION] == round(math.log10(6001) * goals_rules.score_population)
    assert breakdown.parts[ScoreComponent.DIVERSITY] == 2
    assert breakdown.parts[ScoreComponent.WORLDS] == goals_rules.score_world
    assert breakdown.parts[ScoreComponent.DOOMSDAY] == -round(50 / rules.balance.apocalypse_threshold * goals_rules.score_apocalypse_penalty)


async def test_long_peace_completes_once_for_points(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = replace(rules, goals=replace(rules.goals, peace_epochs=1))
    await start_scenario(session, tuned, ScenarioKey.LONG_PEACE)
    with pytest.raises(ConflictError):
        await start_scenario(session, tuned, ScenarioKey.LONG_PEACE)
    result = await epoch_end_goals(make_context(session, tuned, 3, "goals"))
    assert result.completed == (ScenarioKey.LONG_PEACE,)
    assert result.score.parts[ScoreComponent.SCENARIOS] == tuned.goals.peace_points
    await start_scenario(session, tuned, ScenarioKey.LONG_PEACE)
    again = await epoch_end_goals(make_context(session, tuned, 4, "goals"))
    assert again.score.parts[ScoreComponent.SCENARIOS] == tuned.goals.peace_points
    rows = list(await session.scalars(select(ScenarioRow).order_by(ScenarioRow.id)))
    assert [row.points_awarded for row in rows] == [True, False]
    assert god_lines.GOAL_ACHIEVED.key in await chronicle_keys(session)
    assert await session.get(ScoreRow, 4) is not None


async def test_manual_evaluation_does_not_advance_the_peace_counter(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    await start_scenario(session, rules, ScenarioKey.LONG_PEACE)
    await evaluate_now(session, rules)
    await evaluate_now(session, rules)
    row = await session.scalar(select(ScenarioRow))
    assert row is not None and row.counter == 0
    await epoch_end_goals(make_context(session, rules, 3, "goals"))
    await session.refresh(row)
    assert row.counter == 1


async def test_doom_scenario_fails(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    await start_scenario(session, rules, ScenarioKey.DOOM_FAR)
    world.cosmos.doom_clock = rules.balance.apocalypse_threshold
    result = await evaluate_goals(make_context(session, rules, 3, "goals"))
    assert result.failed == (ScenarioKey.DOOM_FAR,)
    assert god_lines.GOAL_LOST.key in await chronicle_keys(session)


async def test_loyal_pantheon_fails_on_new_rebellion(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    await start_scenario(session, rules, ScenarioKey.LOYAL_PANTHEON)
    await declare_rebellion(make_context(session, rules, 2), world.creator, son, "enough", spontaneous=False)
    result = await evaluate_goals(make_context(session, rules, 3, "goals"))
    assert result.failed == (ScenarioKey.LOYAL_PANTHEON,)


async def test_new_horizons_progress(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = replace(rules, goals=replace(rules.goals, horizon_lands=2, horizon_regions=1))
    await start_scenario(session, tuned, ScenarioKey.NEW_HORIZONS)
    await make_entity(session, "New Vale", EntityType.REGION, world_id=world.world.id)
    overview = await goals_overview(session, tuned)
    assert overview.running[0].progress.percent == 50
    await make_entity(session, "New Cave", EntityType.PLACE, world_id=world.world.id, location_id=world.region.id)
    result = await evaluate_goals(make_context(session, tuned, 3, "goals"))
    assert result.completed == (ScenarioKey.NEW_HORIZONS,)


async def test_return_from_death_only_on_resurrection(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    ctx = make_context(session, rules, 3)
    await god_death(ctx, son, "fell", SonDeathCause.OTHER)
    first = await evaluate_goals(make_context(session, rules, 3, "goals"))
    assert AchievementKey.RETURN_FROM_DEATH not in first.earned
    await resurrect_son(ctx, son, "test")
    await goals(make_context(session, rules, 4, "goals"))
    earned = set(await session.scalars(select(AchievementRow.key)))
    assert AchievementKey.RETURN_FROM_DEATH in earned
    assert AchievementKey.WEAPONS_SILENT not in earned
    notifications = list(await session.scalars(select(NotificationRow)))
    assert notifications


async def test_abandon_scenario(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    overview = await start_scenario(session, rules, ScenarioKey.ONE_FAITH)
    scenario_id = overview.running[0].id
    after = await abandon_scenario(session, rules, scenario_id)
    assert not after.running
    assert after.scenarios[1].history[0].status is ScenarioStatus.ABANDONED
    with pytest.raises(NotFoundError):
        await abandon_scenario(session, rules, scenario_id)
