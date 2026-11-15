from aerona.core.grammar import several
from aerona.domain.enums.action import ActionKind
from aerona.engine.cosmos import world_view_control as control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class WorldViewEdit(Edited):
    world_id: int


class WorldViewTarget(Command):
    world_id: int


class RunNow(Command):
    pass


@player_action("world_view:edit", ActionKind.EDIT_RECORD)
async def world_view_edit(scope: PlayerScope, command: WorldViewEdit) -> Effect:
    await control.edit_view(await scope.context("world_view_edit"), command.world_id, command.values, command.release)
    return Effect("The world keeps its new nature.", target_node_id=command.world_id)


@player_action("world_view:reset", ActionKind.EDIT_RECORD)
async def world_view_reset(scope: PlayerScope, command: WorldViewTarget) -> Effect:
    await control.restore_view(await scope.context("world_view_reset"), command.world_id)
    return Effect("The world returns to the nature of its kind.", target_node_id=command.world_id)


@player_action("world_views:run", ActionKind.EDIT_RECORD)
async def world_views_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_views(await scope.context("world_views_run"))
    return Effect(f"The worlds were read: {several(tally.short, 'town ran', 'towns ran')} short of what binds them.")
