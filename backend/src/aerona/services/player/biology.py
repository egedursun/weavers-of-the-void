from aerona.core.grammar import several, spoken
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.biology import BiologyVariant
from aerona.engine.body import variant_control as control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class BiologyEdit(Edited):
    holder_id: int


class BiologyVariantChange(Command):
    holder_id: int
    variant: BiologyVariant


class BiologyTarget(Command):
    holder_id: int


class RunNow(Command):
    pass


@player_action("biology:edit", ActionKind.EDIT_RECORD)
async def biology_edit(scope: PlayerScope, command: BiologyEdit) -> Effect:
    await control.edit_biology(await scope.context("biology_edit"), command.holder_id, command.values, command.release)
    return Effect("The biology keeps its new nature.", target_node_id=command.holder_id)


@player_action("biology_variant:add", ActionKind.EDIT_RECORD)
async def biology_variant_add(scope: PlayerScope, command: BiologyVariantChange) -> Effect:
    await control.set_variant(await scope.context("biology_variant_add"), command.holder_id, command.variant, True)
    return Effect(f"It is now {spoken(command.variant)} in body.", target_node_id=command.holder_id)


@player_action("biology_variant:remove", ActionKind.EDIT_RECORD)
async def biology_variant_remove(scope: PlayerScope, command: BiologyVariantChange) -> Effect:
    await control.set_variant(await scope.context("biology_variant_remove"), command.holder_id, command.variant, False)
    return Effect(f"It is no longer {spoken(command.variant)} in body.", target_node_id=command.holder_id)


@player_action("biology:reset", ActionKind.EDIT_RECORD)
async def biology_reset(scope: PlayerScope, command: BiologyTarget) -> Effect:
    await control.restore_biology(await scope.context("biology_reset"), command.holder_id)
    return Effect("Its biology returns to what its body shows.", target_node_id=command.holder_id)


@player_action("biology_variants:run", ActionKind.EDIT_RECORD)
async def biology_variants_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_biology(await scope.context("biology_variants_run"))
    return Effect(f"Every biology was read: {several(tally.seeded, 'kind of life', 'kinds of life')} first read.")
