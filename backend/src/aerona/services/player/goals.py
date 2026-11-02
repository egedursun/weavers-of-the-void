from aerona.catalog.scenarios import SCENARIOS
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.meta import ScenarioRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.meta import ScenarioKey, ScenarioStatus
from aerona.services.gods import goals
from aerona.services.player.chronicle import tell
from aerona.services.player.lines import SCENARIO_ABANDONED
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class StartScenario(Command):
    key: ScenarioKey


class AbandonScenario(Command):
    scenario_id: int


@player_action("scenario:start", ActionKind.OTHER)
async def start_scenario(scope: PlayerScope, command: StartScenario) -> Effect:
    if command.key not in SCENARIOS:
        raise NotFoundError("No such scenario.")
    overview = await goals.start_scenario(scope.session, scope.rules, command.key)
    return Effect(f"The goal {SCENARIOS[command.key].name(scope.rules)} began.", values={"running": len(overview.running)})


@player_action("scenario:abandon", ActionKind.OTHER)
async def abandon_scenario(scope: PlayerScope, command: AbandonScenario) -> Effect:
    row = await scope.session.get(ScenarioRow, command.scenario_id)
    if row is None or row.status is not ScenarioStatus.RUNNING:
        raise ValidationFailedError("This scenario is not running.")
    await goals.abandon_scenario(scope.session, scope.rules, row.id)
    creator = await scope.creator()
    ctx = await scope.context("abandon_scenario")
    return Effect(await tell(ctx, SCENARIO_ABANDONED, creator=creator.name, name=SCENARIOS[row.key].name(scope.rules)))
