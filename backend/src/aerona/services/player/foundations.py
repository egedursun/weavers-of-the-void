from enum import StrEnum

from pydantic import Field
from sqlalchemy import or_, select

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import several
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.war import WarSide
from aerona.engine.gods.dedication import dedication_of, may_anchor
from aerona.engine.phases.world_age import date_golden_age
from aerona.engine.primitives.holds import ANCHOR_KEY, DEDICATION_KEY, GOLDEN_AGE_KEY, INCITEMENT_KEY, is_held, set_held
from aerona.engine.services.war import war_sides
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

DEDICATION_REASON = "dedicated by the Creator's hand"
UNDEDICATION_REASON = "dedication lifted by the Creator's hand"


class HoldKind(StrEnum):
    INCITEMENT = INCITEMENT_KEY
    GOLDEN_AGE = GOLDEN_AGE_KEY
    DEDICATION = DEDICATION_KEY
    ANCHOR = ANCHOR_KEY


HOLD_LABELS: dict[HoldKind, str] = {
    HoldKind.INCITEMENT: "who incited the war",
    HoldKind.GOLDEN_AGE: "the golden age",
    HoldKind.DEDICATION: "the dedication",
    HoldKind.ANCHOR: "the anchor",
}


class WarIncitement(Command):
    war_id: int
    son_id: int | None = None
    hold: bool = True


class GoldenAgeDate(Command):
    world_id: int
    since_epoch: int = Field(ge=0)
    hold: bool = True


class Dedicate(Command):
    structure_id: int
    son_id: int
    hold: bool = True


class StructureTarget(Command):
    structure_id: int


class SonAnchor(Command):
    son_id: int
    entity_id: int
    hold: bool = True


class SonTarget(Command):
    son_id: int


class HoldFoundation(Command):
    kind: HoldKind
    node_id: int
    held: bool


async def living_son(scope: PlayerScope, son_id: int) -> SonRow:
    son = await scope.session.get(SonRow, son_id)
    if son is None or son.status is SonStatus.DEAD:
        raise NotFoundError("No such living god.")
    return son


async def structure_of(scope: PlayerScope, structure_id: int) -> EntityRow:
    structure = await scope.session.get(EntityRow, structure_id)
    if structure is None or structure.entity_type is not EntityType.STRUCTURE or structure.status is not EntityStatus.CANON:
        raise NotFoundError("No such standing structure.")
    return structure


async def war_of(scope: PlayerScope, war_id: int) -> WarRow:
    war = await scope.session.get(WarRow, war_id)
    if war is None:
        raise NotFoundError("No such war.")
    return war


async def enemy_bonds(scope: PlayerScope, war: WarRow) -> list[BondRow]:
    sides = await war_sides(scope.session, war.id)
    attackers = [side.entity_id for side in sides if side.side is WarSide.ATTACKER]
    defenders = [side.entity_id for side in sides if side.side is WarSide.DEFENDER]
    if not attackers or not defenders:
        return []
    statement = select(BondRow).where(
        BondRow.kind == BondKind.ENEMY,
        BondRow.state == BondState.ACTIVE,
        or_(
            BondRow.source_node_id.in_(attackers) & BondRow.target_node_id.in_(defenders),
            BondRow.source_node_id.in_(defenders) & BondRow.target_node_id.in_(attackers),
        ),
    )
    return list(await scope.session.scalars(statement))


@player_action("war:incite", ActionKind.OTHER)
async def set_incitement(scope: PlayerScope, command: WarIncitement) -> Effect:
    war = await war_of(scope, command.war_id)
    son = await living_son(scope, command.son_id) if command.son_id is not None else None
    war.incited_by_son_id = son.id if son is not None else None
    for bond in await enemy_bonds(scope, war):
        bond.incited_by_son_id = war.incited_by_son_id
    await set_held(scope.session, war.event_entity_id, INCITEMENT_KEY, await scope.epoch(), command.hold)
    held = " and held so" if command.hold else ""
    message = f"The war is now laid at {son.name}'s feet{held}." if son is not None else f"No god is blamed for the war any more{held}."
    return Effect(message, target_node_id=war.event_entity_id)


@player_action("world:date_golden_age", ActionKind.GOLDEN_AGE)
async def set_golden_age_date(scope: PlayerScope, command: GoldenAgeDate) -> Effect:
    epoch = await scope.epoch()
    if command.since_epoch > epoch:
        raise ValidationFailedError(f"A golden age cannot begin after the present age ({epoch}).")
    dated = await date_golden_age(scope.session, command.world_id, command.since_epoch)
    await set_held(scope.session, command.world_id, GOLDEN_AGE_KEY, epoch, command.hold)
    held = "; the engine will keep it so" if command.hold else ""
    return Effect(
        f"The golden age of {several(dated, 'community', 'communities')} now dates from age {command.since_epoch}{held}.", values={"communities": dated}
    )


@player_action("structure:dedicate", ActionKind.OTHER)
async def dedicate_structure(scope: PlayerScope, command: Dedicate) -> Effect:
    structure = await structure_of(scope, command.structure_id)
    son = await living_son(scope, command.son_id)
    epoch = await scope.epoch()
    bonds = BondRepository(scope.session)
    previous = await dedication_of(scope.session, structure.id)
    if previous is not None and previous.id != son.id:
        await bonds.close_between(structure.id, previous.id, [BondKind.WORSHIPS], epoch, UNDEDICATION_REASON)
        await drop_lost_anchor(scope, previous, structure)
    if previous is None or previous.id != son.id:
        await bonds.connect(BondDraft(structure.id, son.id, BondKind.WORSHIPS, epoch, DEDICATION_REASON))
    await set_held(scope.session, structure.id, DEDICATION_KEY, epoch, command.hold)
    return Effect(f"{structure.name} is now dedicated to {son.name}.", target_node_id=structure.id)


@player_action("structure:undedicate", ActionKind.OTHER)
async def undedicate_structure(scope: PlayerScope, command: StructureTarget) -> Effect:
    structure = await structure_of(scope, command.structure_id)
    son = await dedication_of(scope.session, structure.id)
    if son is None:
        raise ValidationFailedError(f"{structure.name} is dedicated to no god.")
    epoch = await scope.epoch()
    await BondRepository(scope.session).close_between(structure.id, son.id, [BondKind.WORSHIPS], epoch, UNDEDICATION_REASON)
    await set_held(scope.session, structure.id, DEDICATION_KEY, epoch, False)
    lost = await drop_lost_anchor(scope, son, structure)
    tail = f" {son.name} lost it as an anchor." if lost else ""
    return Effect(f"{structure.name} is no longer dedicated to {son.name}.{tail}", target_node_id=structure.id)


async def drop_lost_anchor(scope: PlayerScope, son: SonRow, structure: EntityRow) -> bool:
    if son.anchor_entity_id != structure.id or structure.creator_son_id == son.id:
        return False
    son.anchor_entity_id = None
    await set_held(scope.session, son.id, ANCHOR_KEY, await scope.epoch(), False)
    return True


@player_action("son:anchor", ActionKind.CHANGE_ANCHOR)
async def set_anchor(scope: PlayerScope, command: SonAnchor) -> Effect:
    son = await living_son(scope, command.son_id)
    entity = await scope.session.get(EntityRow, command.entity_id)
    if entity is None or entity.status is not EntityStatus.CANON:
        raise NotFoundError("No such living record.")
    if not await may_anchor(scope.session, son, entity):
        raise ValidationFailedError(f"{entity.name} is neither {son.name}'s creation nor a structure dedicated to them.")
    son.anchor_entity_id = entity.id
    await set_held(scope.session, son.id, ANCHOR_KEY, await scope.epoch(), command.hold)
    held = " The god cannot move it." if command.hold else ""
    return Effect(f"{entity.name} now anchors {son.name}'s existence.{held}", target_node_id=entity.id)


@player_action("son:clear_anchor", ActionKind.CHANGE_ANCHOR)
async def clear_anchor(scope: PlayerScope, command: SonTarget) -> Effect:
    son = await living_son(scope, command.son_id)
    if son.anchor_entity_id is None:
        raise ValidationFailedError(f"{son.name} has no anchor.")
    son.anchor_entity_id = None
    await set_held(scope.session, son.id, ANCHOR_KEY, await scope.epoch(), False)
    return Effect(f"{son.name} has no anchor now.")


async def hold_target(scope: PlayerScope, command: HoldFoundation) -> str:
    if command.kind is HoldKind.INCITEMENT:
        war = await scope.session.scalar(select(WarRow).where(WarRow.event_entity_id == command.node_id))
        if war is None:
            raise NotFoundError("No such war.")
        event = await scope.session.get(EntityRow, war.event_entity_id)
        return event.name if event is not None else "the war"
    if command.kind is HoldKind.GOLDEN_AGE:
        world = await scope.session.get(WorldRow, command.node_id)
        if world is None:
            raise NotFoundError("No such world.")
        return world.name
    if command.kind is HoldKind.DEDICATION:
        return (await structure_of(scope, command.node_id)).name
    return (await living_son(scope, command.node_id)).name


@player_action("foundation:hold", ActionKind.OTHER)
async def hold_foundation(scope: PlayerScope, command: HoldFoundation) -> Effect:
    name = await hold_target(scope, command)
    epoch = await scope.epoch()
    label = HOLD_LABELS[command.kind]
    if not command.held and not await is_held(scope.session, command.node_id, command.kind.value, epoch):
        raise ValidationFailedError(f"{label.capitalize()} of {name} is not held.")
    await set_held(scope.session, command.node_id, command.kind.value, epoch, command.held)
    if command.held:
        return Effect(f"{label.capitalize()} of {name} is held: the world keeps it as it is.", target_node_id=command.node_id)
    return Effect(f"{label.capitalize()} of {name} is released to the world's course.", target_node_id=command.node_id)
