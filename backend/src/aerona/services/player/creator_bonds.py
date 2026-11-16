from pydantic import Field

from aerona.core.errors import NotFoundError
from aerona.db.tables.creator_bonds import (
    CHOSEN_FIELDS,
    COVENANT_FIELDS,
    DEPICTION_FIELDS,
    STANDING_FIELDS,
    CovenantRow,
    CreatorChosenRow,
    CreatorDepictionRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.creator import ChosenFavour, CovenantDuty, CreatorPromise
from aerona.domain.enums.entity import EntityType
from aerona.engine.divine.creator_bonds import offer, standing_of
from aerona.engine.powers.control import edit_fields
from aerona.services.player.cosmography import Edited
from aerona.services.player.powers import typed
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class StandingEdit(Edited):
    people_id: int
    hold: bool = True


class CovenantOffer(Command):
    people_id: int
    duty: CovenantDuty = CovenantDuty.WORSHIP
    promise: CreatorPromise = CreatorPromise.PROTECTION
    epochs: int | None = Field(default=None, ge=1, le=1000)


class CovenantEdit(Edited):
    covenant_id: int
    hold: bool = True


class CovenantTarget(Command):
    covenant_id: int


class ChosenPick(Command):
    node_id: int
    favour: ChosenFavour = ChosenFavour.RENOWN


class ChosenEdit(Edited):
    node_id: int
    hold: bool = True


class ChosenTarget(Command):
    node_id: int


class DepictionEdit(Edited):
    people_id: int
    hold: bool = True


async def people_row(scope: PlayerScope, people_id: int) -> EntityRow:
    row = await scope.session.get(EntityRow, people_id)
    if row is None or row.entity_type is not EntityType.PEOPLE:
        raise NotFoundError("No such people.")
    return row


@player_action("creator_standing:edit", ActionKind.EDIT_RECORD)
async def standing_edit(scope: PlayerScope, command: StandingEdit) -> Effect:
    people = await people_row(scope, command.people_id)
    row = await standing_of(await scope.context("creator_standing_edit"), people.id)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(STANDING_FIELDS))
    return Effect(f"How {people.name} hold the Creator: {', '.join(changed) or 'nothing'} set.", people.id)


@player_action("covenant:offer", ActionKind.EDIT_RECORD)
async def covenant_offer(scope: PlayerScope, command: CovenantOffer) -> Effect:
    ctx = await scope.context("covenant_offer")
    people = await people_row(scope, command.people_id)
    row = await offer(ctx, people.id, command.duty, command.promise, ctx.epoch + command.epochs if command.epochs is not None else None)
    return Effect(f"A covenant is offered to {people.name}.", people.id, values={"covenant_id": row.id})


async def covenant_of(scope: PlayerScope, covenant_id: int) -> CovenantRow:
    row = await scope.session.get(CovenantRow, covenant_id)
    if row is None:
        raise NotFoundError("No such covenant.")
    return row


@player_action("covenant:edit", ActionKind.EDIT_RECORD)
async def covenant_edit(scope: PlayerScope, command: CovenantEdit) -> Effect:
    row = await covenant_of(scope, command.covenant_id)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(COVENANT_FIELDS))
    return Effect(f"The covenant: {', '.join(changed) or 'nothing'} set.", row.people_entity_id)


@player_action("covenant:delete", ActionKind.EDIT_RECORD)
async def covenant_delete(scope: PlayerScope, command: CovenantTarget) -> Effect:
    row = await covenant_of(scope, command.covenant_id)
    await scope.session.delete(row)
    return Effect("The covenant is struck from memory.", row.people_entity_id)


@player_action("chosen:choose", ActionKind.EDIT_RECORD)
async def chosen_choose(scope: PlayerScope, command: ChosenPick) -> Effect:
    ctx = await scope.context("chosen_choose")
    if await ctx.session.get(NodeRow, command.node_id) is None:
        raise NotFoundError("No such thing to choose.")
    row = await ctx.session.get(CreatorChosenRow, command.node_id)
    if row is None:
        row = CreatorChosenRow(node_id=command.node_id, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    row.favour = command.favour
    return Effect("The Creator has chosen it.", command.node_id)


async def chosen_of(scope: PlayerScope, node_id: int) -> CreatorChosenRow:
    row = await scope.session.get(CreatorChosenRow, node_id)
    if row is None:
        raise NotFoundError("It is not among the Creator's chosen.")
    return row


@player_action("chosen:edit", ActionKind.EDIT_RECORD)
async def chosen_edit(scope: PlayerScope, command: ChosenEdit) -> Effect:
    row = await chosen_of(scope, command.node_id)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(CHOSEN_FIELDS))
    return Effect(f"The favour of the chosen: {', '.join(changed) or 'nothing'} set.", command.node_id)


@player_action("chosen:release", ActionKind.EDIT_RECORD)
async def chosen_release(scope: PlayerScope, command: ChosenTarget) -> Effect:
    row = await chosen_of(scope, command.node_id)
    await scope.session.delete(row)
    return Effect("It is chosen no longer.", command.node_id)


@player_action("depiction:edit", ActionKind.EDIT_RECORD)
async def depiction_edit(scope: PlayerScope, command: DepictionEdit) -> Effect:
    people = await people_row(scope, command.people_id)
    ctx = await scope.context("depiction_edit")
    row = await ctx.session.get(CreatorDepictionRow, people.id)
    if row is None:
        row = CreatorDepictionRow(people_entity_id=people.id, name=people.name, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(DEPICTION_FIELDS))
    return Effect(f"How {people.name} picture the Creator: {', '.join(changed) or 'nothing'} set.", people.id)
