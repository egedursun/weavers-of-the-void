from aerona.core.grammar import several
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.garden import GardenKind
from aerona.domain.enums.museum import HoardKind, PieceKind
from aerona.engine.museums import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class HoardFound(Command):
    keeper_id: int
    kind: HoardKind


class HoardEdit(Edited):
    collection_id: int


class HoardTarget(Command):
    collection_id: int


class PieceAdd(Command):
    collection_id: int
    kind: PieceKind
    item_id: int


class PieceEdit(Edited):
    piece_id: int


class PieceTarget(Command):
    piece_id: int


class GardenFound(Command):
    town_id: int
    kind: GardenKind


class GardenEdit(Edited):
    garden_id: int


class GardenTarget(Command):
    garden_id: int


class GardenPlant(Command):
    garden_id: int
    species_id: int


class RunNow(Command):
    pass


@player_action("museum:found", ActionKind.EDIT_RECORD)
async def collection_found(scope: PlayerScope, command: HoardFound) -> Effect:
    await control.found_hoard(await scope.context("museum_found"), command.keeper_id, command.kind)
    return Effect("A collection is founded.", target_node_id=command.keeper_id)


@player_action("museum:edit", ActionKind.EDIT_RECORD)
async def collection_edit(scope: PlayerScope, command: HoardEdit) -> Effect:
    hoard = await control.edit_hoard(await scope.context("museum_edit"), command.collection_id, command.values, command.release)
    return Effect("The collection keeps its new values.", target_node_id=hoard.keeper_entity_id)


@player_action("museum:delete", ActionKind.EDIT_RECORD)
async def collection_delete(scope: PlayerScope, command: HoardTarget) -> Effect:
    await control.remove_hoard(await scope.context("museum_delete"), command.collection_id)
    return Effect("The collection is dispersed.")


@player_action("museum_piece:add", ActionKind.EDIT_RECORD)
async def collection_piece_add(scope: PlayerScope, command: PieceAdd) -> Effect:
    await control.add_piece(await scope.context("museum_piece_add"), command.collection_id, command.kind, command.item_id)
    return Effect("The piece joins the collection.", target_node_id=command.item_id)


@player_action("museum_piece:edit", ActionKind.EDIT_RECORD)
async def collection_piece_edit(scope: PlayerScope, command: PieceEdit) -> Effect:
    await control.edit_piece(await scope.context("museum_piece_edit"), command.piece_id, command.values, command.release)
    return Effect("The piece keeps its new values.")


@player_action("museum_piece:remove", ActionKind.EDIT_RECORD)
async def collection_piece_remove(scope: PlayerScope, command: PieceTarget) -> Effect:
    await control.remove_piece(await scope.context("museum_piece_remove"), command.piece_id)
    return Effect("The piece leaves the collection.")


@player_action("museum_piece:restitute", ActionKind.EDIT_RECORD)
async def collection_piece_restitute(scope: PlayerScope, command: PieceTarget) -> Effect:
    home = await control.return_piece(await scope.context("museum_piece_restitute"), command.piece_id)
    return Effect("The piece is given back to those it was taken from.", target_node_id=home.keeper_entity_id)


@player_action("museums:run", ActionKind.EDIT_RECORD)
async def collections_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_hoards(await scope.context("museums_run"))
    return Effect(f"Every collection was read: {several(tally.founded, 'founding', 'foundings')} and {several(tally.gathered, 'piece', 'pieces')} gathered.")


@player_action("garden:found", ActionKind.EDIT_RECORD)
async def garden_found(scope: PlayerScope, command: GardenFound) -> Effect:
    await control.found_garden(await scope.context("garden_found"), command.town_id, command.kind)
    return Effect("A garden is laid out.", target_node_id=command.town_id)


@player_action("garden:edit", ActionKind.EDIT_RECORD)
async def garden_edit(scope: PlayerScope, command: GardenEdit) -> Effect:
    garden = await control.edit_garden(await scope.context("garden_edit"), command.garden_id, command.values, command.release)
    return Effect("The garden keeps its new values.", target_node_id=garden.settlement_entity_id)


@player_action("garden:delete", ActionKind.EDIT_RECORD)
async def garden_delete(scope: PlayerScope, command: GardenTarget) -> Effect:
    await control.remove_garden(await scope.context("garden_delete"), command.garden_id)
    return Effect("The garden is gone.")


@player_action("garden:plant", ActionKind.EDIT_RECORD)
async def garden_plant(scope: PlayerScope, command: GardenPlant) -> Effect:
    garden = await control.plant(await scope.context("garden_plant"), command.garden_id, command.species_id, True)
    return Effect("The garden takes in that kind of life.", target_node_id=garden.settlement_entity_id)


@player_action("garden:uproot", ActionKind.EDIT_RECORD)
async def garden_uproot(scope: PlayerScope, command: GardenPlant) -> Effect:
    garden = await control.plant(await scope.context("garden_uproot"), command.garden_id, command.species_id, False)
    return Effect("That kind of life is taken from the garden.", target_node_id=garden.settlement_entity_id)


@player_action("gardens:run", ActionKind.EDIT_RECORD)
async def gardens_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_gardens(await scope.context("gardens_run"))
    return Effect(f"Every garden was read: {several(tally.founded, 'garden', 'gardens')} laid out, {several(tally.neglected, 'garden', 'gardens')} neglected.")
