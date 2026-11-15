import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.meta import ScenarioRow
from aerona.domain.enums.meta import GoalBasis, GoalComparator, GoalMetric, ScenarioKey, ScenarioStatus
from aerona.services.player import goals
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld


async def _newest(session: AsyncSession) -> ScenarioRow:
    row = await session.scalar(select(ScenarioRow).order_by(ScenarioRow.id.desc()))
    assert row is not None
    return row


async def test_a_preset_starts_with_a_chosen_target_and_deadline(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    effect = await goals.start_scenario(scope, goals.StartScenario(key=ScenarioKey.MANY_WORLDS, target=3, deadline_epochs=4))
    row = await _newest(session)
    assert row.target == 3 and row.deadline_epoch is not None and effect.values["points"] == row.points
    with pytest.raises(ValidationFailedError):
        await goals.start_scenario(scope, goals.StartScenario(key=ScenarioKey.CUSTOM))


async def test_a_goal_of_ones_own_can_be_set_edited_held_and_struck(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    await goals.start_custom_goal(
        scope,
        goals.StartCustomGoal(
            metric=GoalMetric.LANGUAGES, comparator=GoalComparator.AT_LEAST, basis=GoalBasis.GAINED, target=2, hold_epochs=1, title="New tongues"
        ),
    )
    row = await _newest(session)
    assert row.key is ScenarioKey.CUSTOM and row.title == "New tongues" and row.status is ScenarioStatus.RUNNING
    before = row.points
    edited = await goals.edit_scenario(scope, goals.EditScenario(scenario_id=row.id, target=6, deadline_epochs=5, hold_epochs=2, title="More tongues"))
    assert row.target == 6 and row.hold_epochs == 2 and row.title == "More tongues" and row.points > before
    assert edited.values["target"] == 6
    held = await goals.hold_scenario(scope, goals.HoldScenario(scenario_id=row.id, held=True))
    assert row.held and held.values["held"] is True
    await goals.hold_scenario(scope, goals.HoldScenario(scenario_id=row.id, held=False))
    assert not row.held
    await goals.abandon_scenario(scope, goals.AbandonScenario(scenario_id=row.id))
    assert row.status is ScenarioStatus.ABANDONED
    struck = await goals.delete_scenario(scope, goals.ScenarioTarget(scenario_id=row.id))
    assert "struck out" in struck.message
    assert await session.get(ScenarioRow, row.id) is None
    with pytest.raises(NotFoundError):
        await goals.delete_scenario(scope, goals.ScenarioTarget(scenario_id=row.id))


async def test_a_finished_goal_cannot_be_edited_or_held(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    await goals.start_scenario(scope, goals.StartScenario(key=ScenarioKey.DOOM_FAR))
    row = await _newest(session)
    await goals.abandon_scenario(scope, goals.AbandonScenario(scenario_id=row.id))
    with pytest.raises(NotFoundError):
        await goals.edit_scenario(scope, goals.EditScenario(scenario_id=row.id, target=5))
    with pytest.raises(NotFoundError):
        await goals.hold_scenario(scope, goals.HoldScenario(scenario_id=row.id, held=True))
