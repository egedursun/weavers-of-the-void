from aerona.core.grammar import several
from aerona.domain.enums.action import ActionKind
from aerona.engine.lifecycle import end_control as control
from aerona.services.player import guards
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class LifecycleEdit(Edited):
    holder_id: int


class LifecycleTarget(Command):
    holder_id: int


class RunNow(Command):
    pass


@player_action("lifecycle:edit", ActionKind.EDIT_RECORD)
async def lifecycle_edit(scope: PlayerScope, command: LifecycleEdit) -> Effect:
    row = await control.edit_state(await scope.context("lifecycle_edit"), command.holder_id, command.values, command.release)
    return Effect(f"It is now {row.state.value.replace('_', ' ')}.", target_node_id=command.holder_id)


@player_action("lifecycle:reset", ActionKind.EDIT_RECORD)
async def lifecycle_reset(scope: PlayerScope, command: LifecycleTarget) -> Effect:
    row = await control.reset_state(await scope.context("lifecycle_reset"), command.holder_id)
    return Effect(f"Its life is read again from the world: {row.state.value.replace('_', ' ')}.", target_node_id=command.holder_id)


@player_action("lifecycle:destroy", ActionKind.EDIT_RECORD)
async def lifecycle_destroy(scope: PlayerScope, command: LifecycleTarget) -> Effect:
    creator = await scope.creator()
    guards.charge(creator, scope.rules.lifecycle_ends.destroy_cost, "lifecycle_ends.destroy_cost")
    await control.destroy(await scope.context("lifecycle_destroy"), command.holder_id)
    return Effect("The outer being is destroyed for good.", target_node_id=command.holder_id, essence_spent=scope.rules.lifecycle_ends.destroy_cost)


@player_action("lifecycles:run", ActionKind.EDIT_RECORD)
async def lifecycles_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_ends(await scope.context("lifecycles_run"))
    return Effect(f"Every life was read: {several(tally.ended, 'ending', 'endings')} and {several(tally.revived, 'return', 'returns')}.")
