from aerona.core.grammar import spoken
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.world import WorldType
from aerona.domain.enums.world_end import WorldEnd, WorldEndCause
from aerona.engine.cosmos import world_end_control as control
from aerona.engine.cosmos.world_ends import CAUSE_END
from aerona.services.player import guards
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class WorldEndDeclare(Command):
    world_id: int
    cause: WorldEndCause
    state: WorldEnd | None = None
    new_type: WorldType | None = None


class WorldEndEdit(Edited):
    world_id: int


class WorldEndTarget(Command):
    world_id: int


@player_action("world_end:declare", ActionKind.EDIT_RECORD)
async def world_end_declare(scope: PlayerScope, command: WorldEndDeclare) -> Effect:
    creator = await scope.creator()
    guards.charge(creator, scope.rules.world_ends.end_cost, "world_ends.end_cost")
    row = await control.declare_end(
        await scope.context("world_end_declare"), command.world_id, command.state or CAUSE_END[command.cause], command.cause, command.new_type
    )
    return Effect(f"The world is {spoken(row.state)}.", target_node_id=command.world_id, essence_spent=scope.rules.world_ends.end_cost)


@player_action("world_end:edit", ActionKind.EDIT_RECORD)
async def world_end_edit(scope: PlayerScope, command: WorldEndEdit) -> Effect:
    await control.edit_end(await scope.context("world_end_edit"), command.world_id, command.values, command.release)
    return Effect("The record of the end of the world is set.", target_node_id=command.world_id)


@player_action("world_end:remove", ActionKind.EDIT_RECORD)
async def world_end_remove(scope: PlayerScope, command: WorldEndTarget) -> Effect:
    await control.remove_end(await scope.context("world_end_remove"), command.world_id)
    return Effect("The record of the end of the world is struck out; what was lost stays lost.", target_node_id=command.world_id)
