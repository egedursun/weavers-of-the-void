from pydantic import Field
from sqlalchemy import update

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.body import ConditionRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow, ModifierRow
from aerona.db.tables.mind import SkillRow, TraitRow
from aerona.db.tables.mortal import KindVariantRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.body import ConditionKind
from aerona.domain.enums.mind import KindFamily, SkillKind, TraitKind
from aerona.domain.enums.modifier import IncidentRole, ModifierOp
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

STRENGTH_MAX = 400
BASES: dict[KindFamily, frozenset[str]] = {
    KindFamily.TRAIT: frozenset(item.value for item in TraitKind),
    KindFamily.SKILL: frozenset(item.value for item in SkillKind),
    KindFamily.CONDITION: frozenset(item.value for item in ConditionKind),
}
NAME_MAX = 200
NOTE_MAX = 2000
KEY_PATTERN = r"^[a-z][a-z0-9_.]*$"


class CreateVariant(Command):
    family: KindFamily
    base: str = Field(pattern=r"^[a-z_]+$")
    name: str = Field(min_length=1, max_length=NAME_MAX)
    description: str | None = Field(default=None, max_length=NOTE_MAX)
    strength_pct: int = Field(default=100, ge=0, le=STRENGTH_MAX)
    learning_pct: int = Field(default=100, ge=0, le=STRENGTH_MAX)


class EditVariant(Command):
    variant_id: int
    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX)
    description: str | None = Field(default=None, max_length=NOTE_MAX)
    strength_pct: int | None = Field(default=None, ge=0, le=STRENGTH_MAX)
    learning_pct: int | None = Field(default=None, ge=0, le=STRENGTH_MAX)
    hold: bool = True


class VariantField(Command):
    variant_id: int
    field: str = Field(pattern=r"^[a-z_]+$")


class VariantTarget(Command):
    variant_id: int


class AssignVariant(Command):
    family: KindFamily
    row_id: int
    variant_id: int | None = None


class EditModifier(Command):
    modifier_id: int
    magnitude: float | None = None
    op: ModifierOp | None = None
    end_epoch: int | None = Field(default=None, ge=0)
    forever: bool = False
    decay_pct: int | None = Field(default=None, ge=0, le=100)


class Participant(Command):
    node_id: int
    role: IncidentRole


class CreateIncident(Command):
    kind: str = Field(pattern=KEY_PATTERN, max_length=120)
    note: str | None = Field(default=None, max_length=NOTE_MAX)
    magnitude: int = Field(default=0, ge=0, le=100)
    place_entity_id: int | None = None
    participants: list[Participant] = Field(min_length=1)


class IncidentTarget(Command):
    incident_id: int


async def variant_row(scope: PlayerScope, variant_id: int) -> KindVariantRow:
    row = await scope.session.get(KindVariantRow, variant_id)
    if row is None:
        raise NotFoundError("No such kind.")
    return row


@player_action("variant:create", ActionKind.OTHER)
async def create_variant(scope: PlayerScope, command: CreateVariant) -> Effect:
    if command.base not in BASES[command.family]:
        raise ValidationFailedError(f"{command.base} is not a {command.family.value}.")
    row = KindVariantRow(
        family=command.family,
        base=command.base,
        name=command.name.strip(),
        description=command.description,
        strength_pct=command.strength_pct,
        learning_pct=command.learning_pct,
        created_epoch=await scope.epoch(),
        locked=[],
    )
    scope.session.add(row)
    await scope.session.flush()
    return Effect(f"A new {command.family.value}, {row.name}, now exists in the world.", values={"variant_id": row.id})


@player_action("variant:edit", ActionKind.OTHER)
async def edit_variant(scope: PlayerScope, command: EditVariant) -> Effect:
    row = await variant_row(scope, command.variant_id)
    locked = set(row.locked or [])
    for name in ("name", "description", "strength_pct", "learning_pct"):
        value = getattr(command, name)
        if value is not None:
            setattr(row, name, value)
            if command.hold:
                locked.add(name)
    row.locked = sorted(locked)
    return Effect(f"{row.name} was reshaped.")


@player_action("variant:release", ActionKind.OTHER)
async def release_variant(scope: PlayerScope, command: VariantField) -> Effect:
    row = await variant_row(scope, command.variant_id)
    if command.field not in (row.locked or []):
        raise ValidationFailedError(f"{row.name}'s {command.field} is not held.")
    row.locked = [item for item in row.locked if item != command.field]
    return Effect(f"{row.name}'s {command.field.replace('_', ' ')} is free again.")


@player_action("variant:delete", ActionKind.OTHER)
async def delete_variant(scope: PlayerScope, command: VariantTarget) -> Effect:
    row = await variant_row(scope, command.variant_id)
    if row.family is KindFamily.TRAIT:
        await scope.session.execute(update(TraitRow).where(TraitRow.variant_id == row.id).values(variant_id=None))
    elif row.family is KindFamily.SKILL:
        await scope.session.execute(update(SkillRow).where(SkillRow.variant_id == row.id).values(variant_id=None))
    else:
        await scope.session.execute(update(ConditionRow).where(ConditionRow.variant_id == row.id).values(variant_id=None))
    name = row.name
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect(f"{name} is gone from the world; those who bore it keep the plain kind.")


@player_action("variant:assign", ActionKind.OTHER)
async def assign_variant(scope: PlayerScope, command: AssignVariant) -> Effect:
    if command.family is KindFamily.TRAIT:
        raise ValidationFailedError("Give a trait its kind with the trait lever.")
    found = await scope.session.get(SkillRow, command.row_id) if command.family is KindFamily.SKILL else await scope.session.get(ConditionRow, command.row_id)
    if found is None:
        raise NotFoundError(f"No such {command.family.value}.")
    if command.variant_id is not None:
        variant = await variant_row(scope, command.variant_id)
        base = found.skill.value if isinstance(found, SkillRow) else found.kind.value
        if variant.family is not command.family or variant.base != base:
            raise ValidationFailedError(f"{variant.name} is not a kind of {base.replace('_', ' ')}.")
    found.variant_id = command.variant_id
    return Effect("The kind was set.", target_node_id=found.holder_node_id if isinstance(found, SkillRow) else found.bearer_node_id)


@player_action("modifier:edit", ActionKind.OTHER)
async def edit_modifier(scope: PlayerScope, command: EditModifier) -> Effect:
    row = await scope.session.get(ModifierRow, command.modifier_id)
    if row is None:
        raise NotFoundError("No such modifier.")
    if command.magnitude is not None:
        row.magnitude = command.magnitude
    if command.op is not None:
        row.op = command.op
    if command.forever:
        row.end_epoch = None
    elif command.end_epoch is not None:
        if command.end_epoch < row.start_epoch:
            raise ValidationFailedError("A modifier cannot end before it begins.")
        row.end_epoch = command.end_epoch
    if command.decay_pct is not None:
        row.decay_pct = command.decay_pct
    return Effect("The modifier was changed in place.", target_node_id=row.target_node_id)


@player_action("incident:create", ActionKind.OTHER)
async def create_incident(scope: PlayerScope, command: CreateIncident) -> Effect:
    for participant in command.participants:
        if await scope.session.get(NodeRow, participant.node_id) is None:
            raise ValidationFailedError("Every participant must be a record that exists.")
    row = IncidentRow(kind=command.kind, epoch=await scope.epoch(), note=command.note, magnitude=command.magnitude, place_entity_id=command.place_entity_id)
    scope.session.add(row)
    await scope.session.flush()
    for position, participant in enumerate(command.participants):
        scope.session.add(IncidentParticipantRow(incident_id=row.id, node_id=participant.node_id, role=participant.role, position=position))
    await scope.session.flush()
    return Effect("An incident was set into the record.", target_node_id=command.participants[0].node_id, values={"incident_id": row.id})


@player_action("incident:remove", ActionKind.OTHER)
async def remove_incident(scope: PlayerScope, command: IncidentTarget) -> Effect:
    row = await scope.session.get(IncidentRow, command.incident_id)
    if row is None:
        raise NotFoundError("No such incident.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The incident was struck from the record.")
