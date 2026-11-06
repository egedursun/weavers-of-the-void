from aerona.core.errors import NotFoundError
from aerona.db.tables.society import ReverenceRow
from aerona.domain.enums.action import ActionKind
from aerona.engine.phases.native_faith import run_native_faith, syncretize
from aerona.services.player import guards
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


@player_action("faith:unsyncretize", ActionKind.OTHER)
async def unweave(scope: PlayerScope, command: Syncretism) -> Effect:
    row = await scope.session.get(ReverenceRow, (command.entity_id, command.god_id))
    entity = await guards.entity(scope.session, command.entity_id)
    if row is None:
        raise NotFoundError(f"{entity.name} does not revere that god.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect(f"{entity.name} no longer reveres that old god beside its own.", entity.id)
