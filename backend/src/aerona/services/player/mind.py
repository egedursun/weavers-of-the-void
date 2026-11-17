from pydantic import Field
from sqlalchemy import delete

from aerona.catalog.mind import MEMORIES, SKILLS, TRAITS, VALUE_LABELS
from aerona.catalog.mind_split import ATTRIBUTES, FACETS, IDEAS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an
from aerona.db.record_context import current_scope
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.mind import (
    ATTRIBUTE_MAX,
    ATTRIBUTE_MIN,
    FACET_MAX,
    FACET_MIN,
    MIND_LOCKS,
    SKILL_MAX,
    SKILL_MIN,
    VALUE_MAX,
    VALUE_MIN,
    IdeaRow,
    MemoryRow,
    SkillRow,
    TraitRow,
)
from aerona.db.tables.mortal import KindVariantRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.folkways import IdeaStrain
from aerona.domain.enums.limits import RELATION_MAX, RELATION_MIN
from aerona.domain.enums.mind import (
    Attribute,
    CareerChange,
    Facet,
    IdeaKind,
    IdeaSource,
    IdeaState,
    KindFamily,
    MemoryKind,
    NeedKind,
    PressureKind,
    SkillKind,
    SkillSource,
    ThoughtKind,
    TraitKind,
    TraitSource,
    ValueAxis,
    ValueHolder,
)
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.mind.book import (
    PRESSURE_TYPES,
    Holder,
    add_trait,
    ensure_mind_row,
    has_mind,
    holder_kind,
    load_holder,
    remove_trait,
    set_skill,
    stored_values,
    write_needs,
    write_pressures,
    write_values,
)
from aerona.engine.mind.ideas import Encounter, internalise, reject, take_up
from aerona.engine.mind.memories import remember
from aerona.engine.mind.needs import NEED_LOCK, role_status
from aerona.engine.mind.skills import ROLE_LOCK, CareerMove
from aerona.engine.mind.split import (
    ATTRIBUTE_LOCK,
    FACET_LOCK,
    Bodied,
    attributes_of,
    culture_mean,
    estimate,
    facets_of,
    has_attributes,
    has_facets,
    store_attributes,
    write_facets,
)
from aerona.engine.mind.thoughts import think
from aerona.engine.mind.values import VALUE_LOCK
from aerona.engine.recording.record import record
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
    variant_id: int | None = None


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


class SetAttributes(MindTarget):
    values: dict[Attribute, int]
    lock: bool = True


class SetFacets(MindTarget):
    values: dict[Facet, int]
    lock: bool = True


class ImplantIdea(MindTarget):
    idea: IdeaKind
    progress: int = Field(default=0, ge=0, le=PERCENT)
    state: IdeaState = IdeaState.INCUBATING
    source: IdeaSource = IdeaSource.PLAYER
    source_id: int | None = None


class IdeaTarget(Command):
    idea_id: int


class EditIdea(IdeaTarget):
    progress: int | None = Field(default=None, ge=0, le=PERCENT)
    state: IdeaState | None = None
    source: IdeaSource | None = None
    source_id: int | None = None
    clear_source: bool = False
    strain: IdeaStrain | None = None


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
    variant = await scope.session.get(KindVariantRow, command.variant_id) if command.variant_id is not None else None
    if command.variant_id is not None and (variant is None or variant.family is not KindFamily.TRAIT or variant.base != command.trait.value):
        raise ValidationFailedError(f"That is not a kind of {TRAITS[command.trait].label.lower()}.")
    if not await add_trait(scope.session, node.id, command.trait, TraitSource.PLAYER, await scope.epoch()):
        raise ValidationFailedError(f"{node.name} is already {TRAITS[command.trait].label.lower()}.")
    held = await scope.session.get(TraitRow, (node.id, command.trait))
    if held is not None and variant is not None:
        held.variant_id = variant.id
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
    return Effect(f"{node.name}'s {label(command.need.value)} is now {command.value:d}.", target_node_id=node.id)


@player_action("mind:pressure", ActionKind.OTHER)
async def set_pressure(scope: PlayerScope, command: SetPressure) -> Effect:
    node = await holder_of(scope, command.node_id)
    if not isinstance(node, EntityRow) or node.entity_type not in PRESSURE_TYPES:
        raise ValidationFailedError("Only peoples and settlements feel pressures.")
    await mind_for(scope, node)
    await write_pressures(scope.session, node.id, {command.pressure: command.value})
    await hold(scope, node, NEED_LOCK, command.lock)
    return Effect(f"{node.name}'s {label(command.pressure.value)} is now {command.value:d}.", target_node_id=node.id)


@player_action("mind:role", ActionKind.OTHER)
async def set_role(scope: PlayerScope, command: SetRole) -> Effect:
    node = await holder_of(scope, command.node_id)
    if not isinstance(node, EntityRow) or node.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only mortals follow a calling.")
    move = CareerMove(node.mortal_role or MortalRole.COMMONER, command.role, CareerChange.PLAYER)
    node.mortal_role = command.role
    await hold(scope, node, ROLE_LOCK, command.lock)
    if move.old is not move.new:
        ctx = await scope.context("mind_role")
        rose = role_status(scope.rules, move.new) >= role_status(scope.rules, move.old)
        await think(scope.session, scope.rules, node.id, ThoughtKind.ROSE_IN_RANK if rose else ThoughtKind.FELL_IN_RANK, ctx.epoch)
        await record(
            ctx,
            f"skill.career_{move.reason.value}",
            roles={IncidentRole.SUBJECT: node.id, IncidentRole.AUTHORITY: acting.actor_node_id if (acting := current_scope()) is not None else None},
            facts={"reason": move.reason, "before": move.old, "after": move.new},
        )
    return Effect(f"{node.name} is now {an(label(command.role.value))}.", target_node_id=node.id)


async def bodied_of(scope: PlayerScope, node_id: int) -> Bodied:
    found = await bodied_of_any(scope, node_id)
    if found is None:
        raise NotFoundError("Nothing lives there.")
    return found


async def hold_where_minded(scope: PlayerScope, node: Bodied, field: str, held: bool) -> None:
    if has_mind(node) and held:
        await hold(scope, node, field, True)


@player_action("mind:attributes", ActionKind.OTHER)
async def set_attributes(scope: PlayerScope, command: SetAttributes) -> Effect:
    node = await bodied_of(scope, command.node_id)
    if not has_attributes(node):
        raise ValidationFailedError(f"{node.name} has no body or mind to measure.")
    current = await attributes_of(scope.session, node.id) or estimate(node)
    for which, value in command.values.items():
        current[which] = max(ATTRIBUTE_MIN, min(ATTRIBUTE_MAX, value))
    await store_attributes(scope.session, node, current)
    await hold_where_minded(scope, node, ATTRIBUTE_LOCK, command.lock)
    changed = ", ".join(f"{ATTRIBUTES[which].label.lower()} {current[which]}" for which in command.values)
    return Effect(f"{node.name} now has {changed}.", target_node_id=node.id)


@player_action("mind:facets", ActionKind.OTHER)
async def set_facets(scope: PlayerScope, command: SetFacets) -> Effect:
    node = await bodied_of(scope, command.node_id)
    if not has_facets(node):
        raise ValidationFailedError(f"{node.name} has no temperament to shape.")
    current = await facets_of(scope.session, node.id) or await culture_mean(scope.session, scope.rules, node)
    for facet, value in command.values.items():
        current[facet] = max(FACET_MIN, min(FACET_MAX, value))
    await write_facets(scope.session, node.id, current)
    await hold_where_minded(scope, node, FACET_LOCK, command.lock)
    changed = ", ".join(f"{FACETS[facet].label.lower()} {current[facet]:+d}" for facet in command.values)
    return Effect(f"{node.name}'s temperament is now {changed}.", target_node_id=node.id)


async def source_exists(scope: PlayerScope, source_id: int | None) -> None:
    if source_id is not None and await bodied_of_any(scope, source_id) is None:
        raise ValidationFailedError("An idea can only come from a record that exists.")


async def bodied_of_any(scope: PlayerScope, node_id: int) -> Bodied | None:
    entity = await scope.session.get(EntityRow, node_id)
    if entity is not None:
        return entity
    son = await scope.session.get(SonRow, node_id)
    if son is not None:
        return son
    return await scope.session.get(ForeignGodRow, node_id)


async def settle_idea(scope: PlayerScope, node: Holder, row: IdeaRow, state: IdeaState) -> None:
    epoch = await scope.epoch()
    if state is IdeaState.INTERNALISED and row.state is not IdeaState.INTERNALISED:
        await internalise(scope.session, scope.rules, node, row, epoch)
    elif state is IdeaState.REJECTED:
        reject(row, epoch)
    elif state is IdeaState.INCUBATING:
        row.state, row.finished_epoch = IdeaState.INCUBATING, None


@player_action("mind:idea", ActionKind.OTHER)
async def implant_idea(scope: PlayerScope, command: ImplantIdea) -> Effect:
    node = await holder_of(scope, command.node_id)
    if not has_facets(node):
        raise ValidationFailedError(f"{node.name} does not turn ideas over.")
    await source_exists(scope, command.source_id)
    await mind_for(scope, node)
    row = await take_up(scope.session, node.id, Encounter(command.idea, command.source, command.source_id), await scope.epoch(), progress=command.progress)
    if row is None:
        raise ValidationFailedError(f"{node.name} already knows {IDEAS[command.idea].label.lower()}.")
    await settle_idea(scope, node, row, command.state)
    await scope.session.flush()
    return Effect(f"{node.name} now turns over {IDEAS[command.idea].label.lower()}.", target_node_id=node.id, values={"idea_id": row.id})


async def idea_row(scope: PlayerScope, idea_id: int) -> IdeaRow:
    row = await scope.session.get(IdeaRow, idea_id)
    if row is None:
        raise NotFoundError("No such idea.")
    return row


@player_action("mind:idea_edit", ActionKind.OTHER)
async def edit_idea(scope: PlayerScope, command: EditIdea) -> Effect:
    row = await idea_row(scope, command.idea_id)
    node = await holder_of(scope, row.holder_node_id)
    await source_exists(scope, command.source_id)
    if command.progress is not None:
        row.progress = command.progress
    if command.source is not None:
        row.source = command.source
    if command.source_id is not None:
        row.source_node_id = command.source_id
    if command.clear_source:
        row.source_node_id = None
    if command.strain is not None:
        row.strain = command.strain
    if command.state is not None:
        await settle_idea(scope, node, row, command.state)
    await scope.session.flush()
    return Effect(f"{node.name}'s {IDEAS[row.idea].label.lower()} was changed.", target_node_id=node.id)


@player_action("mind:idea_remove", ActionKind.OTHER)
async def remove_idea(scope: PlayerScope, command: IdeaTarget) -> Effect:
    row = await idea_row(scope, command.idea_id)
    holder, idea = row.holder_node_id, row.idea
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect(f"The idea of {IDEAS[idea].label.lower()} was taken away.", target_node_id=holder)
