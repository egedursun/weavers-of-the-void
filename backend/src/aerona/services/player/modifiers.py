from pydantic import Field

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import ModifierRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.engine.interconnect.derived import DERIVED_SOURCES
from aerona.engine.primitives.modifiers import GUARD_SOURCES, UNMODIFIABLE_KEYS, VIRTUAL_KEYS, ModifierDraft, add_modifier
from aerona.engine.primitives.stats import has_stat
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

KEY_PATTERN = r"^[a-z][a-z0-9_.:]*$"
GROUP_PATTERN = r"^[a-z][a-z0-9_.:-]*$"
PLAYER_REASON = "player.modifier"


class CreateModifier(Command):
    node_id: int
    key: str = Field(pattern=KEY_PATTERN)
    op: ModifierOp
    magnitude: float
    source_kind: ModifierSource = ModifierSource.PLAYER
    source_node_id: int | None = None
    stacking_group: str | None = Field(default=None, pattern=GROUP_PATTERN, max_length=60)
    epochs: int | None = Field(default=None, ge=1)
    decay_pct: int | None = Field(default=None, ge=0, le=100)


class EditModifier(Command):
    modifier_id: int
    key: str | None = Field(default=None, pattern=KEY_PATTERN)
    op: ModifierOp | None = None
    magnitude: float | None = None
    source_kind: ModifierSource | None = None
    source_node_id: int | None = None
    clear_source_node: bool = False
    stacking_group: str | None = Field(default=None, pattern=GROUP_PATTERN, max_length=60)
    clear_stacking_group: bool = False
    epochs: int | None = Field(default=None, ge=1)
    endless: bool = False
    decay_pct: int | None = Field(default=None, ge=0, le=100)
    clear_decay: bool = False


class HoldModifier(Command):
    modifier_id: int


def reason_for(source: ModifierSource) -> str:
    return PLAYER_REASON if source is ModifierSource.PLAYER else f"modifier.{source.value}"


async def _node(scope: PlayerScope, node_id: int) -> NodeRow:
    node = await scope.session.get(NodeRow, node_id)
    if node is None:
        raise NotFoundError("No such record.")
    return node


async def _modifier(scope: PlayerScope, modifier_id: int) -> ModifierRow:
    row = await scope.session.get(ModifierRow, modifier_id)
    if row is None or row.source_kind in GUARD_SOURCES:
        raise NotFoundError("No such modifier.")
    return row


async def _check_key(scope: PlayerScope, node_id: int, key: str) -> None:
    if key in UNMODIFIABLE_KEYS:
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} is a conserved count; no modifier may bend it.")
    entity = await scope.session.get(EntityRow, node_id)
    if key not in VIRTUAL_KEYS and (entity is None or not has_stat(entity, key)):
        raise ValidationFailedError(f"This record has no {key.replace('_', ' ')} to bend.")


def _check_shape(op: ModifierOp, magnitude: float) -> None:
    if op is ModifierOp.MULTIPLY and magnitude < 0:
        raise ValidationFailedError("A multiplying modifier cannot be negative.")


def _change(op: ModifierOp, magnitude: float) -> str:
    return f"times {magnitude:g}" if op is ModifierOp.MULTIPLY else f"{magnitude:+g}"


@player_action("modifier:create", ActionKind.OTHER)
async def create_modifier(scope: PlayerScope, command: CreateModifier) -> Effect:
    node = await _node(scope, command.node_id)
    if command.source_kind in GUARD_SOURCES:
        raise ValidationFailedError("Pins and held-back mechanics have their own levers.")
    await _check_key(scope, node.id, command.key)
    _check_shape(command.op, command.magnitude)
    if command.source_node_id is not None:
        await _node(scope, command.source_node_id)
    epoch = await scope.epoch()
    draft = ModifierDraft(
        node.id,
        command.key,
        command.op,
        command.magnitude,
        command.source_kind,
        reason_for(command.source_kind),
        start_epoch=epoch,
        source_node_id=command.source_node_id,
        stacking_group=command.stacking_group,
        end_epoch=None if command.epochs is None else epoch + command.epochs - 1,
        decay_pct=command.decay_pct,
    )
    row = await add_modifier(scope.session, draft, held=command.source_kind in DERIVED_SOURCES)
    label = command.source_kind.value.replace("_", " ")
    return Effect(
        f"{node.name}'s {command.key.replace('_', ' ')} gains {an(label)} modifier of {_change(command.op, command.magnitude)}.",
        target_node_id=node.id,
        created_ids=(row.id,),
    )


@player_action("modifier:edit", ActionKind.OTHER)
async def edit_modifier(scope: PlayerScope, command: EditModifier) -> Effect:
    row = await _modifier(scope, command.modifier_id)
    if command.source_kind in GUARD_SOURCES:
        raise ValidationFailedError("Pins and held-back mechanics have their own levers.")
    if command.key is not None:
        await _check_key(scope, row.target_node_id, command.key)
        row.target_key = command.key
    op = command.op or row.op
    magnitude = row.magnitude if command.magnitude is None else command.magnitude
    _check_shape(op, magnitude)
    row.op, row.magnitude = op, magnitude
    if command.source_kind is not None:
        row.source_kind = command.source_kind
        row.reason_key = (
            reason_for(command.source_kind) if row.reason_key in (PLAYER_REASON, *(f"modifier.{item.value}" for item in ModifierSource)) else row.reason_key
        )
    if command.clear_source_node:
        row.source_node_id = None
    elif command.source_node_id is not None:
        row.source_node_id = (await _node(scope, command.source_node_id)).id
    if command.clear_stacking_group:
        row.stacking_group = None
    elif command.stacking_group is not None:
        row.stacking_group = command.stacking_group
    epoch = await scope.epoch()
    if command.endless:
        row.end_epoch = None
    elif command.epochs is not None:
        row.end_epoch = max(row.start_epoch, epoch + command.epochs - 1)
    if command.clear_decay:
        row.decay_pct = None
    elif command.decay_pct is not None:
        row.decay_pct = command.decay_pct
    row.held = row.held or row.source_kind in DERIVED_SOURCES
    kept = " The engine keeps it as you set it." if row.held else ""
    return Effect(f"The modifier on {row.target_key.replace('_', ' ')} is now {_change(row.op, row.magnitude)}.{kept}", target_node_id=row.target_node_id)


@player_action("modifier:hold", ActionKind.OTHER)
async def hold_modifier(scope: PlayerScope, command: HoldModifier) -> Effect:
    row = await _modifier(scope, command.modifier_id)
    if row.held:
        raise ValidationFailedError("This modifier is already held.")
    row.held = True
    return Effect(
        f"The modifier on {row.target_key.replace('_', ' ')} is held: the engine will not redraw, fade or replace it.", target_node_id=row.target_node_id
    )


@player_action("modifier:release", ActionKind.OTHER)
async def release_modifier(scope: PlayerScope, command: HoldModifier) -> Effect:
    row = await _modifier(scope, command.modifier_id)
    if not row.held:
        raise ValidationFailedError("This modifier is not held.")
    row.held = False
    tail = " Its source will redraw it next epoch." if row.source_kind in DERIVED_SOURCES else ""
    return Effect(f"The modifier on {row.target_key.replace('_', ' ')} is released.{tail}", target_node_id=row.target_node_id)
