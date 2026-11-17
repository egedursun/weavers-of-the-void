from pydantic import Field
from sqlalchemy import delete

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import several
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow, ModifierRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.engine.interconnect.registry import MECHANICS, suppression_key
from aerona.engine.primitives.modifiers import ModifierDraft, add_modifier
from aerona.engine.primitives.stats import has_stat, set_stats, stat_bounds
from aerona.services.player import engine_control
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

KEY_PATTERN = r"^[a-z][a-z0-9_.:]*$"
PLAYER_REASON = "player.modifier"
PIN_REASON = "player.pin"
SUPPRESSION_REASON = "player.suppression"


class PinField(Command):
    node_id: int
    key: str = Field(pattern=KEY_PATTERN)
    epochs: int | None = Field(default=None, ge=1)


class UnpinField(Command):
    node_id: int
    key: str = Field(pattern=KEY_PATTERN)


class SuppressMechanic(Command):
    node_id: int
    mechanic: str = Field(pattern=KEY_PATTERN)
    epochs: int = Field(ge=1)


class UnsuppressMechanic(Command):
    node_id: int
    mechanic: str = Field(pattern=KEY_PATTERN)


class AddModifier(Command):
    node_id: int
    key: str = Field(pattern=KEY_PATTERN)
    op: ModifierOp
    magnitude: float
    epochs: int | None = Field(default=None, ge=1)
    decay_pct: int | None = Field(default=None, ge=0, le=100)


class RemoveModifier(Command):
    modifier_id: int


class RunMechanic(Command):
    mechanic: str = Field(pattern=KEY_PATTERN)
    target_node_id: int | None = None


async def _node(scope: PlayerScope, node_id: int) -> NodeRow:
    node = await scope.session.get(NodeRow, node_id)
    if node is None:
        raise NotFoundError("No such record.")
    return node


def _end(epoch: int, epochs: int | None) -> int | None:
    return None if epochs is None else epoch + epochs - 1


async def _clear(scope: PlayerScope, node_id: int, key: str, source: ModifierSource) -> int:
    result = await scope.session.execute(
        delete(ModifierRow).where(ModifierRow.target_node_id == node_id, ModifierRow.target_key == key, ModifierRow.source_kind == source)
    )
    return int(getattr(result, "rowcount", 0) or 0)


@player_action("lever:pin", ActionKind.OTHER)
async def pin_field(scope: PlayerScope, command: PinField) -> Effect:
    node = await _node(scope, command.node_id)
    epoch = await scope.epoch()
    await _clear(scope, node.id, command.key, ModifierSource.PIN)
    draft = ModifierDraft(node.id, command.key, ModifierOp.ADD, 0, ModifierSource.PIN, PIN_REASON, start_epoch=epoch, end_epoch=_end(epoch, command.epochs))
    await add_modifier(scope.session, draft)
    span = f" for {several(command.epochs, 'epoch', 'epochs')}" if command.epochs else ""
    return Effect(f"{node.name}'s {command.key} is pinned{span}: no mechanic can change it.", target_node_id=node.id)


@player_action("lever:unpin", ActionKind.OTHER)
async def unpin_field(scope: PlayerScope, command: UnpinField) -> Effect:
    node = await _node(scope, command.node_id)
    if not await _clear(scope, node.id, command.key, ModifierSource.PIN):
        raise ValidationFailedError(f"{node.name}'s {command.key} is not pinned.")
    return Effect(f"{node.name}'s {command.key} is free again.", target_node_id=node.id)


@player_action("lever:suppress", ActionKind.OTHER)
async def suppress_mechanic(scope: PlayerScope, command: SuppressMechanic) -> Effect:
    node = await _node(scope, command.node_id)
    epoch = await scope.epoch()
    key = suppression_key(command.mechanic)
    await _clear(scope, node.id, key, ModifierSource.SUPPRESSION)
    draft = ModifierDraft(
        node.id, key, ModifierOp.ADD, 0, ModifierSource.SUPPRESSION, SUPPRESSION_REASON, start_epoch=epoch, end_epoch=_end(epoch, command.epochs)
    )
    await add_modifier(scope.session, draft)
    return Effect(f"{command.mechanic} is suppressed on {node.name} for {several(command.epochs, 'epoch', 'epochs')}.", target_node_id=node.id)


@player_action("lever:unsuppress", ActionKind.OTHER)
async def unsuppress_mechanic(scope: PlayerScope, command: UnsuppressMechanic) -> Effect:
    node = await _node(scope, command.node_id)
    if not await _clear(scope, node.id, suppression_key(command.mechanic), ModifierSource.SUPPRESSION):
        raise ValidationFailedError(f"{command.mechanic} is not suppressed on {node.name}.")
    return Effect(f"{command.mechanic} acts on {node.name} again.", target_node_id=node.id)


@player_action("modifier:add", ActionKind.OTHER)
async def add_player_modifier(scope: PlayerScope, command: AddModifier) -> Effect:
    node = await _node(scope, command.node_id)
    epoch = await scope.epoch()
    if command.op is ModifierOp.MULTIPLY and command.magnitude < 0:
        raise ValidationFailedError("A multiplying modifier cannot be negative.")
    draft = ModifierDraft(
        node.id,
        command.key,
        command.op,
        command.magnitude,
        ModifierSource.PLAYER,
        PLAYER_REASON,
        start_epoch=epoch,
        end_epoch=_end(epoch, command.epochs),
        decay_pct=command.decay_pct,
    )
    row = await add_modifier(scope.session, draft)
    change = f"times {command.magnitude:g}" if command.op is ModifierOp.MULTIPLY else f"{command.magnitude:+g}"
    return Effect(f"{node.name}'s {command.key} gains a modifier of {change}.", target_node_id=node.id, created_ids=(row.id,))


@player_action("modifier:remove", ActionKind.OTHER)
async def remove_player_modifier(scope: PlayerScope, command: RemoveModifier) -> Effect:
    row = await scope.session.get(ModifierRow, command.modifier_id)
    if row is None:
        raise NotFoundError("No such modifier.")
    target = row.target_node_id
    await scope.session.delete(row)
    return Effect("The modifier was removed.", target_node_id=target)


@player_action("lever:run", ActionKind.OTHER)
async def run_mechanic(scope: PlayerScope, command: RunMechanic) -> Effect:
    mechanic = MECHANICS.get(command.mechanic)
    if mechanic is None:
        raise NotFoundError(f"No mechanic is called {command.mechanic}.")
    if not mechanic.phases:
        raise ValidationFailedError(f"{mechanic.title} runs only when its events happen; it has no step to run.")
    if command.target_node_id is not None:
        await _node(scope, command.target_node_id)
    messages = [
        (await engine_control.run_phase(scope, engine_control.RunPhase(phase=phase, target_node_id=command.target_node_id))).message
        for phase in mechanic.phases
    ]
    return Effect(" ".join(messages), target_node_id=command.target_node_id)


class AnnotateIncident(Command):
    incident_id: int
    note: str | None = Field(default=None, max_length=2000)


@player_action("incident:annotate", ActionKind.OTHER)
async def annotate_incident(scope: PlayerScope, command: AnnotateIncident) -> Effect:
    row = await scope.session.get(IncidentRow, command.incident_id)
    if row is None:
        raise NotFoundError("No such incident.")
    row.note = command.note.strip() if command.note and command.note.strip() else None
    return Effect("Your note was written beside the incident." if row.note else "Your note was taken away.")


class SetField(Command):
    node_id: int
    key: str = Field(pattern=KEY_PATTERN)
    value: int


@player_action("lever:set", ActionKind.OTHER)
async def set_field(scope: PlayerScope, command: SetField) -> Effect:
    entity = await scope.session.get(EntityRow, command.node_id)
    if entity is None:
        raise NotFoundError("Only a record's own values can be set here.")
    if not has_stat(entity, command.key):
        raise ValidationFailedError(f"{entity.name} has no {command.key.replace('_', ' ')}.")
    low, high = stat_bounds(scope.rules, entity, command.key)
    if not low <= command.value <= high:
        raise ValidationFailedError(f"{command.key.replace('_', ' ').capitalize()} must lie between {low} and {high}.")
    set_stats(entity, **{command.key: command.value})
    return Effect(f"{entity.name}'s {command.key.replace('_', ' ')} is now {command.value:d}.", target_node_id=entity.id)
