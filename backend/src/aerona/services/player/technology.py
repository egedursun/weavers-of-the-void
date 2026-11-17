from pydantic import Field

from aerona.core.errors import NotFoundError
from aerona.core.grammar import spoken
from aerona.db.tables.node import NodeRow
from aerona.db.tables.technology import TECH_LEVEL_MAX, TechnologyProfileRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.eras import TechFamily
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class TechSet(Command):
    node_id: int
    family: TechFamily
    level: int = Field(ge=0, le=TECH_LEVEL_MAX)
    hold: bool = True


class TechTarget(Command):
    node_id: int
    family: TechFamily


@player_action("technology:set", ActionKind.EDIT_RECORD)
async def technology_set(scope: PlayerScope, command: TechSet) -> Effect:
    if await scope.session.get(NodeRow, command.node_id) is None:
        raise NotFoundError("No such thing.")
    row = await scope.session.get(TechnologyProfileRow, (command.node_id, command.family))
    epoch = (await scope.context("technology_set")).epoch
    if row is None:
        row = TechnologyProfileRow(holder_node_id=command.node_id, family=command.family, level=command.level, updated_epoch=epoch, locked=[])
        scope.session.add(row)
    row.level, row.updated_epoch = command.level, epoch
    row.locked = ["level"] if command.hold else []
    await scope.session.flush()
    return Effect(f"Its {spoken(command.family)} stands at level {command.level}.", command.node_id)


@player_action("technology:release", ActionKind.EDIT_RECORD)
async def technology_release(scope: PlayerScope, command: TechTarget) -> Effect:
    row = await scope.session.get(TechnologyProfileRow, (command.node_id, command.family))
    if row is None:
        raise NotFoundError("No level is set for that family.")
    row.locked = []
    return Effect(f"Its {spoken(command.family)} follows what it knows again.", command.node_id)


@player_action("technology:delete", ActionKind.EDIT_RECORD)
async def technology_delete(scope: PlayerScope, command: TechTarget) -> Effect:
    row = await scope.session.get(TechnologyProfileRow, (command.node_id, command.family))
    if row is None:
        raise NotFoundError("No level is set for that family.")
    await scope.session.delete(row)
    return Effect(f"Its own level of {spoken(command.family)} is struck; it takes that of its people or world.", command.node_id)
