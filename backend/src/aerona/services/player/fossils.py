from aerona.core.grammar import several
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.fossil import FossilSource
from aerona.engine.ecology import fossil_control as control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class FossilPlace(Command):
    region_id: int
    source: FossilSource
    richness: int = 30


class FossilEdit(Edited):
    bed_id: int


class FossilTarget(Command):
    bed_id: int


class RunNow(Command):
    pass


@player_action("fossil_bed:create", ActionKind.EDIT_RECORD)
async def fossil_bed_create(scope: PlayerScope, command: FossilPlace) -> Effect:
    bed = await control.place_bed(await scope.context("fossil_bed_create"), command.region_id, command.source, command.richness)
    return Effect("Remains lie hidden in that land now.", target_node_id=bed.region_entity_id)


@player_action("fossil_bed:edit", ActionKind.EDIT_RECORD)
async def fossil_bed_edit(scope: PlayerScope, command: FossilEdit) -> Effect:
    bed = await control.edit_bed(await scope.context("fossil_bed_edit"), command.bed_id, command.values, command.release)
    return Effect("The fossil bed keeps its new values.", target_node_id=bed.region_entity_id)


@player_action("fossil_bed:delete", ActionKind.EDIT_RECORD)
async def fossil_bed_delete(scope: PlayerScope, command: FossilTarget) -> Effect:
    await control.remove_bed(await scope.context("fossil_bed_delete"), command.bed_id)
    return Effect("The fossil bed is gone.")


@player_action("fossil_bed:reveal", ActionKind.EDIT_RECORD)
async def fossil_bed_reveal(scope: PlayerScope, command: FossilTarget) -> Effect:
    bed = await control.reveal_bed(await scope.context("fossil_bed_reveal"), command.bed_id)
    return Effect("The remains come to light.", target_node_id=bed.region_entity_id)


@player_action("fossils:run", ActionKind.EDIT_RECORD)
async def fossils_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_fossils(await scope.context("fossils_run"))
    return Effect(f"Every fossil bed was read: {several(tally.laid, 'bed', 'beds')} laid down and {several(tally.found, 'find', 'finds')}.")
