from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.pantheon import (
    PANTHEON_FIELDS,
    SYNCRETISM_FIELDS,
    TIE_FIELDS,
    PantheonStructureRow,
    PantheonTieRow,
    SyncretismRow,
)
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.foreign_god import PantheonTie
from aerona.engine.powers.control import edit_fields
from aerona.services.player.cosmography import Edited
from aerona.services.player.powers import typed
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class PantheonEdit(Edited):
    world_id: int
    hold: bool = True


class TieSet(Command):
    god_id: int
    other_id: int
    tie: PantheonTie = PantheonTie.KIN


class TieEdit(Edited):
    god_id: int
    other_id: int
    hold: bool = True


class TieTarget(Command):
    god_id: int
    other_id: int


class SyncretismMake(Command):
    foreign_god_id: int
    son_id: int
    people_id: int


class SyncretismEdit(Edited):
    syncretism_id: int
    hold: bool = True


class SyncretismTarget(Command):
    syncretism_id: int


async def god_node(scope: PlayerScope, node_id: int) -> NodeRow:
    if await scope.session.get(ForeignGodRow, node_id) is None and await scope.session.get(SonRow, node_id) is None:
        raise NotFoundError("No such god.")
    node = await scope.session.get(NodeRow, node_id)
    if node is None:
        raise NotFoundError("No such god.")
    return node


@player_action("pantheon:edit", ActionKind.EDIT_RECORD)
async def pantheon_edit(scope: PlayerScope, command: PantheonEdit) -> Effect:
    world = await scope.session.get(WorldRow, command.world_id)
    if world is None:
        raise NotFoundError("No such world.")
    ctx = await scope.context("pantheon_edit")
    row = await ctx.session.get(PantheonStructureRow, world.id)
    if row is None:
        row = PantheonStructureRow(world_id=world.id, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(PANTHEON_FIELDS))
    return Effect(f"The gods of {world.name}: {', '.join(changed) or 'nothing'} set.", world.id)


@player_action("pantheon_tie:set", ActionKind.EDIT_RECORD)
async def tie_set(scope: PlayerScope, command: TieSet) -> Effect:
    if command.god_id == command.other_id:
        raise ValidationFailedError("A god holds no tie to itself.")
    await god_node(scope, command.god_id)
    await god_node(scope, command.other_id)
    ctx = await scope.context("pantheon_tie_set")
    row = await ctx.session.get(PantheonTieRow, (command.god_id, command.other_id))
    if row is None:
        row = PantheonTieRow(god_node_id=command.god_id, other_node_id=command.other_id, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    row.tie = command.tie
    return Effect("The tie between the gods is set.", command.god_id)


async def tie_of(scope: PlayerScope, god_id: int, other_id: int) -> PantheonTieRow:
    row = await scope.session.get(PantheonTieRow, (god_id, other_id))
    if row is None:
        raise NotFoundError("No such tie between these gods.")
    return row


@player_action("pantheon_tie:edit", ActionKind.EDIT_RECORD)
async def tie_edit(scope: PlayerScope, command: TieEdit) -> Effect:
    row = await tie_of(scope, command.god_id, command.other_id)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(TIE_FIELDS))
    return Effect(f"The tie: {', '.join(changed) or 'nothing'} set.", command.god_id)


@player_action("pantheon_tie:delete", ActionKind.EDIT_RECORD)
async def tie_delete(scope: PlayerScope, command: TieTarget) -> Effect:
    row = await tie_of(scope, command.god_id, command.other_id)
    await scope.session.delete(row)
    return Effect("The tie between the gods is undone.", command.god_id)


@player_action("syncretism:create", ActionKind.EDIT_RECORD)
async def syncretism_create(scope: PlayerScope, command: SyncretismMake) -> Effect:
    god = await scope.session.get(ForeignGodRow, command.foreign_god_id)
    son = await scope.session.get(SonRow, command.son_id)
    people = await scope.session.get(EntityRow, command.people_id)
    if god is None or son is None:
        raise NotFoundError("No such god.")
    if people is None or people.entity_type is not EntityType.PEOPLE:
        raise NotFoundError("No such people.")
    ctx = await scope.context("syncretism_create")
    row = SyncretismRow(foreign_god_id=god.id, son_id=son.id, people_entity_id=people.id, dominant_node_id=son.id, since_epoch=ctx.epoch)
    row.locked = []
    ctx.session.add(row)
    await ctx.session.flush()
    return Effect(f"{people.name} hold {son.name} and {god.name} as one.", people.id, values={"syncretism_id": row.id})


async def syncretism_of(scope: PlayerScope, syncretism_id: int) -> SyncretismRow:
    row = await scope.session.get(SyncretismRow, syncretism_id)
    if row is None:
        raise NotFoundError("No such joining of gods.")
    return row


@player_action("syncretism:edit", ActionKind.EDIT_RECORD)
async def syncretism_edit(scope: PlayerScope, command: SyncretismEdit) -> Effect:
    row = await syncretism_of(scope, command.syncretism_id)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(SYNCRETISM_FIELDS))
    return Effect(f"The joined worship: {', '.join(changed) or 'nothing'} set.", row.people_entity_id)


@player_action("syncretism:delete", ActionKind.EDIT_RECORD)
async def syncretism_delete(scope: PlayerScope, command: SyncretismTarget) -> Effect:
    row = await syncretism_of(scope, command.syncretism_id)
    await scope.session.delete(row)
    return Effect("The two gods are held apart again.", row.people_entity_id)
