from pydantic import Field

from aerona.constants.schema import TITLE_MAX_LENGTH
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.meta import ScenarioRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.meta import GoalBasis, GoalComparator, GoalMetric, ScenarioKey, ScenarioStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.gods.goals import scenario_name
from aerona.engine.recording.record import record
from aerona.services.gods import goals
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class StartScenario(Command):
    key: ScenarioKey
    target: int | None = Field(None, ge=1)
    deadline_epochs: int | None = Field(None, ge=1)


class StartCustomGoal(Command):
    metric: GoalMetric
    comparator: GoalComparator = GoalComparator.AT_LEAST
    basis: GoalBasis = GoalBasis.TOTAL
    target: int = Field(ge=0)
    hold_epochs: int = Field(0, ge=0)
    deadline_epochs: int | None = Field(None, ge=1)
    title: str | None = Field(None, max_length=TITLE_MAX_LENGTH)


class ScenarioTarget(Command):
    scenario_id: int


class EditScenario(ScenarioTarget):
    target: int = Field(ge=0)
    deadline_epochs: int | None = Field(None, ge=1)
    hold_epochs: int = Field(0, ge=0)
    title: str | None = Field(None, max_length=TITLE_MAX_LENGTH)


class HoldScenario(ScenarioTarget):
    held: bool


class AbandonScenario(ScenarioTarget):
    pass


def latest(overview: goals.GoalsOverview) -> goals.RunningScenario:
    return max(overview.running, key=lambda item: item.id)


@player_action("scenario:start", ActionKind.OTHER)
async def start_scenario(scope: PlayerScope, command: StartScenario) -> Effect:
    if command.key is ScenarioKey.CUSTOM:
        raise ValidationFailedError("A goal of your own is set with its measure, target and hold.")
    overview = await goals.start_scenario(scope.session, scope.rules, command.key, command.target, command.deadline_epochs)
    started = latest(overview)
    return Effect(f"The goal {started.name} began.", values={"running": len(overview.running), "points": started.points, "target": started.target})


@player_action("scenario:custom", ActionKind.OTHER)
async def start_custom_goal(scope: PlayerScope, command: StartCustomGoal) -> Effect:
    overview = await goals.start_custom(
        scope.session,
        scope.rules,
        metric=command.metric,
        comparator=command.comparator,
        basis=command.basis,
        target=command.target,
        hold_epochs=command.hold_epochs,
        deadline_epochs=command.deadline_epochs,
        title=command.title,
    )
    started = latest(overview)
    return Effect(f"The goal {started.name} began.", values={"running": len(overview.running), "points": started.points, "target": started.target})


@player_action("scenario:edit", ActionKind.OTHER)
async def edit_scenario(scope: PlayerScope, command: EditScenario) -> Effect:
    overview = await goals.edit_scenario(
        scope.session,
        scope.rules,
        command.scenario_id,
        target=command.target,
        deadline_epochs=command.deadline_epochs,
        hold_epochs=command.hold_epochs,
        title=command.title,
    )
    edited = next(item for item in overview.running if item.id == command.scenario_id)
    return Effect(f"The goal {edited.name} now aims at {edited.target}.", values={"points": edited.points, "target": edited.target})


@player_action("scenario:hold", ActionKind.OTHER)
async def hold_scenario(scope: PlayerScope, command: HoldScenario) -> Effect:
    overview = await goals.hold_scenario(scope.session, scope.rules, command.scenario_id, command.held)
    held = next(item for item in overview.running if item.id == command.scenario_id)
    state = "is held; the epochs pass it by" if command.held else "is measured again"
    return Effect(f"The goal {held.name} {state}.", values={"held": command.held})


@player_action("scenario:abandon", ActionKind.OTHER)
async def abandon_scenario(scope: PlayerScope, command: AbandonScenario) -> Effect:
    row = await scope.session.get(ScenarioRow, command.scenario_id)
    if row is None or row.status is not ScenarioStatus.RUNNING:
        raise ValidationFailedError("This scenario is not running.")
    name = scenario_name(row)
    await goals.abandon_scenario(scope.session, scope.rules, row.id)
    creator = await scope.creator()
    ctx = await scope.context("abandon_scenario")
    return Effect(
        (await record(ctx, "player.goals.abandoned", roles={IncidentRole.ACTOR: creator.id}, facts={"name": name}, kind=ChronicleKind.CREATOR_HAND)).text
    )


@player_action("scenario:delete", ActionKind.OTHER)
async def delete_scenario(scope: PlayerScope, command: ScenarioTarget) -> Effect:
    row = await scope.session.get(ScenarioRow, command.scenario_id)
    if row is None:
        raise NotFoundError("No such scenario.")
    name = scenario_name(row)
    overview = await goals.delete_scenario(scope.session, scope.rules, row.id)
    return Effect(f"The record of the goal {name} was struck out.", values={"running": len(overview.running)})
