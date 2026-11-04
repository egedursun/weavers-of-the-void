from pydantic import Field
from sqlalchemy import delete

from aerona.catalog.mind import MEMORIES, SKILLS, TRAITS, VALUE_LABELS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MIND_LOCKS, SKILL_MAX, SKILL_MIN, VALUE_MAX, VALUE_MIN, MemoryRow, SkillRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.limits import RELATION_MAX, RELATION_MIN
from aerona.domain.enums.mind import MemoryKind, NeedKind, PressureKind, SkillKind, SkillSource, TraitKind, TraitSource, ValueAxis, ValueHolder
from aerona.engine.mind.book import (
    PRESSURE_TYPES,
    Holder,
    add_trait,
    ensure_mind_row,
    holder_kind,
    load_holder,
    remove_trait,
    set_skill,
    stored_values,
    write_needs,
    write_pressures,
    write_values,
)
from aerona.engine.mind.memories import remember
from aerona.engine.mind.needs import NEED_LOCK
from aerona.engine.mind.skills import ROLE_LOCK
from aerona.engine.mind.values import VALUE_LOCK
from aerona.engine.services.community_relations import refresh_relation
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SKILL_LOCK = "skills"
TRAIT_LOCK = "traits"


class MindTarget(Command):
    node_id: int


class SetValues(MindTarget):
    values: dict[ValueAxis, int]
    lock: bool = True


class LockMind(MindTarget):
    field: str = Field(pattern=r"^[a-z]+$")


class TraitCommand(MindTarget):
    trait: TraitKind


class SetSkill(MindTarget):
    skill: SkillKind
    level: int = Field(ge=SKILL_MIN, le=SKILL_MAX)
    lock: bool = False
    subject_id: int | None = None


class SkillTarget(MindTarget):
    skill: SkillKind
    subject_id: int | None = None


class EditSkill(Command):
    skill_id: int
    level: int | None = Field(default=None, ge=SKILL_MIN, le=SKILL_MAX)
    xp: int | None = Field(default=None, ge=0)
    peak: int | None = Field(default=None, ge=SKILL_MIN, le=SKILL_MAX)
    subject_id: int | None = None
    clear_subject: bool = False


class AddMemory(Command):
    holder_id: int
    subject_id: int
    kind: MemoryKind
    magnitude: int = Field(ge=RELATION_MIN, le=RELATION_MAX)
    decay_pct: int | None = Field(default=None, ge=0, le=PERCENT)
    note: str | None = Field(default=None, max_length=120)


class MemoryTarget(Command):
    memory_id: int


class EditMemory(MemoryTarget):
    magnitude: int | None = Field(default=None, ge=RELATION_MIN, le=RELATION_MAX)
    decay_pct: int | None = Field(default=None, ge=0, le=PERCENT)


class SetNeed(MindTarget):
    need: NeedKind
    value: int = Field(ge=0, le=PERCENT)
    lock: bool = True


class SetPressure(MindTarget):
    pressure: PressureKind
    value: int = Field(ge=0, le=PERCENT)
    lock: bool = True


class SetRole(MindTarget):
    role: MortalRole
    lock: bool = True


def label(text: str) -> str:
    return text.replace("_", " ")


async def holder_of(scope: PlayerScope, node_id: int) -> Holder:
    found = await load_holder(scope.session, node_id)
    if found is None:
        raise NotFoundError("No mind lives there.")
    return found


async def mind_for(scope: PlayerScope, node: Holder) -> None:
    await ensure_mind_row(scope.session, node, await scope.epoch())


async def hold(scope: PlayerScope, node: Holder, field: str, held: bool) -> None:
    row, _ = await ensure_mind_row(scope.session, node, await scope.epoch())
    locked = set(row.locked or [])
    if held:
        locked.add(field)
    row.locked = sorted(locked)
    await scope.session.flush()


@player_action("mind:values", ActionKind.OTHER)
async def set_values(scope: PlayerScope, command: SetValues) -> Effect:
    node = await holder_of(scope, command.node_id)
    kind = holder_kind(node)
    if kind is None or kind is ValueHolder.COMMUNITY:
        raise ValidationFailedError(f"{node.name} takes its values from its people; change the people instead.")
    current = await stored_values(scope.session, kind, node.id)
    for axis, value in command.values.items():
        current[axis] = max(VALUE_MIN, min(VALUE_MAX, value))
    await write_values(scope.session, kind, node.id, current)
    await hold(scope, node, VALUE_LOCK, command.lock)
    changed = ", ".join(f"{VALUE_LABELS[axis][1].lower()} {current[axis]}" for axis in command.values)
    return Effect(f"{node.name} now holds {changed}.", target_node_id=node.id)


@player_action("mind:lock", ActionKind.OTHER)
async def lock_mind(scope: PlayerScope, command: LockMind) -> Effect:
    if command.field not in MIND_LOCKS:
        raise ValidationFailedError(f"{label(command.field)} cannot be held.")
    node = await holder_of(scope, command.node_id)
    await hold(scope, node, command.field, True)
    return Effect(f"{node.name}'s {label(command.field)} are held as they are.", target_node_id=node.id)


@player_action("mind:unlock", ActionKind.OTHER)
async def unlock_mind(scope: PlayerScope, command: LockMind) -> Effect:
    node = await holder_of(scope, command.node_id)
    row, _ = await ensure_mind_row(scope.session, node, await scope.epoch())
    if command.field not in (row.locked or []):
        raise ValidationFailedError(f"{node.name}'s {label(command.field)} are not held.")
    row.locked = [field for field in row.locked if field != command.field]
    return Effect(f"{node.name}'s {label(command.field)} change with the world again.", target_node_id=node.id)


@player_action("mind:trait", ActionKind.OTHER)
async def give_trait(scope: PlayerScope, command: TraitCommand) -> Effect:
    node = await holder_of(scope, command.node_id)
    await mind_for(scope, node)
    if not await add_trait(scope.session, node.id, command.trait, TraitSource.PLAYER, await scope.epoch()):
        raise ValidationFailedError(f"{node.name} is already {TRAITS[command.trait].label.lower()}.")
    await hold(scope, node, TRAIT_LOCK, True)
    return Effect(f"{node.name} is now {TRAITS[command.trait].label.lower()}.", target_node_id=node.id)


@player_action("mind:trait_remove", ActionKind.OTHER)
async def take_trait(scope: PlayerScope, command: TraitCommand) -> Effect:
    node = await holder_of(scope, command.node_id)
    if not await remove_trait(scope.session, node.id, command.trait):
        raise ValidationFailedError(f"{node.name} is not {TRAITS[command.trait].label.lower()}.")
    await hold(scope, node, TRAIT_LOCK, True)
    return Effect(f"{node.name} is no longer {TRAITS[command.trait].label.lower()}.", target_node_id=node.id)


@player_action("mind:skill", ActionKind.OTHER)
async def give_skill(scope: PlayerScope, command: SetSkill) -> Effect:
    node = await holder_of(scope, command.node_id)
    if not isinstance(node, EntityRow) or node.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only mortals learn skills.")
    await mind_for(scope, node)
    await set_skill(
        scope.session, node.id, command.skill, command.level, epoch=await scope.epoch(), source=SkillSource.PLAYER, subject_node_id=command.subject_id
    )
    await hold(scope, node, SKILL_LOCK, command.lock)
    return Effect(f"{node.name}'s {SKILLS[command.skill].label.lower()} is now {command.level}.", target_node_id=node.id)


@player_action("mind:skill_remove", ActionKind.OTHER)
async def forget_skill(scope: PlayerScope, command: SkillTarget) -> Effect:
    node = await holder_of(scope, command.node_id)
    subject = SkillRow.subject_node_id == command.subject_id if command.subject_id is not None else SkillRow.subject_node_id.is_(None)
    result = await scope.session.execute(delete(SkillRow).where(SkillRow.holder_node_id == node.id, SkillRow.skill == command.skill, subject))
    if not getattr(result, "rowcount", 0):
        raise ValidationFailedError(f"{node.name} has no {SKILLS[command.skill].label.lower()} to forget.")
    return Effect(f"{node.name} forgot {SKILLS[command.skill].label.lower()}.", target_node_id=node.id)


@player_action("mind:skill_edit", ActionKind.OTHER)
async def edit_skill(scope: PlayerScope, command: EditSkill) -> Effect:
    row = await scope.session.get(SkillRow, command.skill_id)
    if row is None:
        raise NotFoundError("No such skill.")
    if command.subject_id is not None:
        if await load_holder(scope.session, command.subject_id) is None and await scope.session.get(EntityRow, command.subject_id) is None:
            raise ValidationFailedError("A skill can only be about a record that exists.")
        row.subject_node_id = command.subject_id
    if command.clear_subject:
        row.subject_node_id = None
    if command.level is not None:
        row.level = command.level
    if command.xp is not None:
        row.xp = command.xp
    if command.peak is not None:
        row.peak = command.peak
    row.peak = max(row.peak, row.level)
    await scope.session.flush()
    return Effect(f"The {SKILLS[row.skill].label.lower()} skill was changed.", target_node_id=row.holder_node_id)


@player_action("mind:memory", ActionKind.OTHER)
async def add_memory(scope: PlayerScope, command: AddMemory) -> Effect:
    holder = await holder_of(scope, command.holder_id)
    subject = await scope.session.get(EntityRow, command.subject_id) or await load_holder(scope.session, command.subject_id)
    if subject is None or holder.id == command.subject_id:
        raise ValidationFailedError("A memory needs someone else to be about.")
    await mind_for(scope, holder)
    epoch = await scope.epoch()
    row = await remember(
        scope.session,
        scope.rules,
        holder_id=holder.id,
        subject_id=command.subject_id,
        kind=command.kind,
        magnitude=command.magnitude,
        epoch=epoch,
        note=command.note,
        decay_pct=command.decay_pct,
        forced=True,
    )
    if row is None:
        raise ValidationFailedError("The memory would weigh nothing.")
    await refresh_pair(scope, holder.id, command.subject_id)
    return Effect(
        f"{holder.name} now remembers that {subject.name}: {MEMORIES[command.kind].label.lower()}.", target_node_id=holder.id, values={"memory_id": row.id}
    )


async def memory_row(scope: PlayerScope, memory_id: int) -> MemoryRow:
    row = await scope.session.get(MemoryRow, memory_id)
    if row is None:
        raise NotFoundError("No such memory.")
    return row


async def refresh_pair(scope: PlayerScope, first: int, second: int) -> None:
    entities = [await scope.session.get(EntityRow, node) for node in (first, second)]
    if all(entity is not None and entity.entity_type in PRESSURE_TYPES | {EntityType.CULT, EntityType.FACTION} for entity in entities):
        await refresh_relation(scope.session, scope.rules, await scope.epoch(), first, second)


@player_action("mind:memory_edit", ActionKind.OTHER)
async def edit_memory(scope: PlayerScope, command: EditMemory) -> Effect:
    row = await memory_row(scope, command.memory_id)
    if command.magnitude is not None:
        row.magnitude = command.magnitude
    if command.decay_pct is not None:
        row.decay_pct = command.decay_pct
    await scope.session.flush()
    await refresh_pair(scope, row.holder_node_id, row.subject_node_id)
    return Effect("The memory was changed.", target_node_id=row.holder_node_id)


@player_action("mind:memory_remove", ActionKind.OTHER)
async def forget_memory(scope: PlayerScope, command: MemoryTarget) -> Effect:
    row = await memory_row(scope, command.memory_id)
    holder, subject = row.holder_node_id, row.subject_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    await refresh_pair(scope, holder, subject)
    return Effect("The memory was forgotten.", target_node_id=holder)


@player_action("mind:need", ActionKind.OTHER)
async def set_need(scope: PlayerScope, command: SetNeed) -> Effect:
    node = await holder_of(scope, command.node_id)
    if not isinstance(node, EntityRow) or node.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only mortals have needs.")
    await mind_for(scope, node)
    await write_needs(scope.session, node.id, {command.need: command.value})
    await hold(scope, node, NEED_LOCK, command.lock)
    return Effect(f"{node.name}'s {label(command.need.value)} is now {command.value}.", target_node_id=node.id)


@player_action("mind:pressure", ActionKind.OTHER)
async def set_pressure(scope: PlayerScope, command: SetPressure) -> Effect:
    node = await holder_of(scope, command.node_id)
    if not isinstance(node, EntityRow) or node.entity_type not in PRESSURE_TYPES:
        raise ValidationFailedError("Only peoples and settlements feel pressures.")
    await mind_for(scope, node)
    await write_pressures(scope.session, node.id, {command.pressure: command.value})
    await hold(scope, node, NEED_LOCK, command.lock)
    return Effect(f"{node.name}'s {label(command.pressure.value)} is now {command.value}.", target_node_id=node.id)


@player_action("mind:role", ActionKind.OTHER)
async def set_role(scope: PlayerScope, command: SetRole) -> Effect:
    node = await holder_of(scope, command.node_id)
    if not isinstance(node, EntityRow) or node.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only mortals follow a calling.")
    node.mortal_role = command.role
    await hold(scope, node, ROLE_LOCK, command.lock)
    return Effect(f"{node.name} is now a {label(command.role.value)}.", target_node_id=node.id)
