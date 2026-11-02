from aerona.domain.enums.action import ActionKind
from aerona.engine.phases.native_faith import run_native_faith, syncretize
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class Syncretism(Command):
    entity_id: int
    god_id: int


class Empty(Command):
    pass


@player_action("faith:syncretize", ActionKind.SYNCRETIZE_FAITH)
async def weave(scope: PlayerScope, command: Syncretism) -> Effect:
    return Effect(await syncretize(scope.session, scope.rules, command.entity_id, command.god_id), command.entity_id)


@player_action("faith:native_run", ActionKind.OTHER)
async def run_now(scope: PlayerScope, command: Empty) -> Effect:
    await run_native_faith(scope.session, scope.rules)
    return Effect("The old gods stirred among the natives of their worlds.")
