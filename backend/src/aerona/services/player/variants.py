from pydantic import Field
from sqlalchemy import update

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an, spoken
from aerona.db.tables.body import ConditionRow
from aerona.db.tables.mind import SkillRow, TraitRow
from aerona.db.tables.mortal import KindVariantRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.body import ConditionKind
from aerona.domain.enums.mind import KindFamily, SkillKind, TraitKind
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

STRENGTH_MAX = 400
BASES: dict[KindFamily, frozenset[str]] = {
    KindFamily.TRAIT: frozenset(item.value for item in TraitKind),
    KindFamily.SKILL: frozenset(item.value for item in SkillKind),
    KindFamily.CONDITION: frozenset(item.value for item in ConditionKind),
}
NAME_MAX = 200
NOTE_MAX = 2000


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


async def variant_row(scope: PlayerScope, variant_id: int) -> KindVariantRow:
    row = await scope.session.get(KindVariantRow, variant_id)
    if row is None:
        raise NotFoundError("No such kind.")
    return row


@player_action("variant:create", ActionKind.OTHER)
async def create_variant(scope: PlayerScope, command: CreateVariant) -> Effect:
    if command.base not in BASES[command.family]:
        raise ValidationFailedError(f"{command.base} is not {an(spoken(command.family))}.")
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
    return Effect(f"A new {spoken(command.family)}, {row.name}, now exists in the world.", values={"variant_id": row.id})


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
        raise NotFoundError(f"No such {spoken(command.family)}.")
    if command.variant_id is not None:
        variant = await variant_row(scope, command.variant_id)
        base = found.skill.value if isinstance(found, SkillRow) else found.kind.value
        if variant.family is not command.family or variant.base != base:
            raise ValidationFailedError(f"{variant.name} is not a kind of {base.replace('_', ' ')}.")
    found.variant_id = command.variant_id
    return Effect("The kind was set.", target_node_id=found.holder_node_id if isinstance(found, SkillRow) else found.bearer_node_id)
