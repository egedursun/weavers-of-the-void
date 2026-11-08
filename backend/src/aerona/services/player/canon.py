from enum import StrEnum

from sqlalchemy import or_, select, update

from aerona.catalog.bonds import bond_spec
from aerona.constants.player import ENTITY_TEXT_MAX_LENGTH, THREAD_HEADLINE_LENGTH
from aerona.constants.schema import (
    MAP_NOTE_COLOR_MAX_LENGTH,
    MAP_NOTE_MAX_LENGTH,
    NAME_MAX_LENGTH,
    PRIVATE_NOTE_MAX_LENGTH,
    SUBTYPE_MAX_LENGTH,
    TITLE_MAX_LENGTH,
)
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.names import normalize_name
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow, EntityTagRow, EntityTraitRow
from aerona.db.tables.epochs import EpochRow
from aerona.db.tables.lore import CanonFactRow, FolkBeliefRow, LexemeRow, ThreadRow
from aerona.db.tables.meta import ImageRow, MapNoteRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.bond import DERIVED_BOND_KINDS, BondKind, BondState
from aerona.domain.enums.chronicle import ThreadStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.node import NodeKind
from aerona.engine.gods.rewards import adjust_reward
from aerona.engine.primitives.canon_facts import FactDraft, add_manual_fact, retract_fact
from aerona.engine.primitives.folk_names import folk_god_name, guarded_names
from aerona.engine.primitives.naming import Namer
from aerona.engine.primitives.renames import rewrite_name
from aerona.engine.primitives.threads import advance_story, close_story, open_story, story_entities
from aerona.services.player import guards
from aerona.services.player.chronicle import hand, tell
from aerona.services.player.lines import (
    ALSO_KNOWN_AS,
    BOND_ADDED,
    BOND_BROKEN,
    CANON_RESTORED,
    CANON_STRUCK,
    EPOCH_EDITED,
    MERGED,
    RECORD_EDITED,
    RECORD_RENAMED,
    RESTORE_NOTE,
    STRIKE_NOTE,
    THREAD_ADVANCED,
    THREAD_CLOSED,
    THREAD_DEFAULT_CLOSING,
    THREAD_OPENED,
)
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

BOND_NODE_KINDS = frozenset({NodeKind.ENTITY, NodeKind.SON})
DEFAULT_BOND_TEXT = "the god's command"


class ConfirmationWord(StrEnum):
    MERGE = "MERGE"


class CanonVerdict(StrEnum):
    CANON = "canon"
    REJECTED = "rejected"


class SetCanon(Command):
    entity_id: int
    status: CanonVerdict


class EditRecord(Command):
    entity_id: int
    name: str | None = None
    title: str | None = None
    subtype: str | None = None
    description: str | None = None
    image_prompt: str | None = None
    is_water: bool | None = None
    is_underworld: bool | None = None


class OpenThread(Command):
    text: str
    related_ids: tuple[int, ...] = ()


class CloseThread(Command):
    thread_id: int
    how: str = ""


class AddFact(Command):
    subject_id: int
    relation: str
    object_id: int | None = None
    object_text: str | None = None


class FactTarget(Command):
    fact_id: int


class EditBelief(Command):
    people_id: int
    son_id: int | None = None
    name: str | None = None
    narrative: str
    misconception: str | None = None


class AddBond(Command):
    source_id: int
    target_id: int
    kind: BondKind
    description: str | None = None


class BondTarget(Command):
    bond_id: int


class AddMapNote(Command):
    world_id: int
    x: float
    y: float
    text: str
    color: str | None = None


class MapNoteTarget(Command):
    note_id: int


class MergeRecords(Command):
    entity_id: int
    other_id: int
    confirm: str


class Favorite(Command):
    entity_id: int
    favorite: bool = True


class PrivateNote(Command):
    entity_id: int
    text: str = ""


@player_action("canon:set", ActionKind.CANON_STRIKE)
async def set_canon(scope: PlayerScope, command: SetCanon) -> Effect:
    record = await guards.entity(scope.session, command.entity_id)
    creator = await scope.creator()
    epoch = await scope.epoch()
    entities = EntityRepository(scope.session)
    bonds = BondRepository(scope.session)
    ctx = await scope.context("canon")
    if command.status is CanonVerdict.CANON:
        if record.status is EntityStatus.CANON:
            raise ValidationFailedError(f"{record.name} is already canon.")
        if record.status is not EntityStatus.REJECTED:
            raise ValidationFailedError(
                f"Only a rejected record can be restored; {record.name} is {record.status.value} (the dead come back only through resurrection)."
            )
        await entities.set_status(record, EntityStatus.CANON, epoch, RESTORE_NOTE.format(creator=creator.name))
        reopened = await bonds.reopen_after_restore(record.id)
        await adjust_reward(scope.session, scope.rules, record.id, 0, thread=False, reason=creator.name)
        message = await tell(ctx, CANON_RESTORED, ids=[record.id], creator=creator.name, entity=record.name)
        return Effect(message, record.id, kind=ActionKind.CANON_RESTORE, tool="canon:restore", values={"bonds_reopened": reopened})
    if record.status is EntityStatus.REJECTED:
        raise ValidationFailedError(f"{record.name} is already struck from canon.")
    hidden = await bonds.hide_for_rejection(record.id, epoch)
    tools = scope.rules.son_tools
    await adjust_reward(
        scope.session, scope.rules, record.id, tools.reject_take_back_pct, thread=bool(tools.reject_reverts_thread), raise_only=True, reason=creator.name
    )
    await entities.set_status(record, EntityStatus.REJECTED, epoch, STRIKE_NOTE.format(creator=creator.name))
    message = await tell(ctx, CANON_STRUCK, ids=[record.id], creator=creator.name, entity=record.name)
    return Effect(message, record.id, kind=ActionKind.CANON_STRIKE, tool="canon:strike", values={"bonds_hidden": hidden})


def region_flags(record: EntityRow, command: EditRecord) -> list[str]:
    if command.is_water is None and command.is_underworld is None:
        return []
    if record.entity_type is not EntityType.REGION:
        raise ValidationFailedError("Only a region can be water, land or a realm of the dead.")
    fields: list[str] = []
    if command.is_water is not None:
        record.is_water = command.is_water
        fields.append("water")
    if command.is_underworld is not None:
        record.is_underworld = command.is_underworld
        fields.append("realm of the dead" if command.is_underworld else "no longer a realm of the dead")
    return fields


@player_action("record:edit", ActionKind.EDIT_RECORD)
async def edit_record(scope: PlayerScope, command: EditRecord) -> Effect:
    record = await guards.entity(scope.session, command.entity_id)
    ctx = await scope.context("edit_record")
    creator = await scope.creator()
    fields: list[str] = []
    messages: list[str] = []
    if command.name is not None and normalize_name(command.name) != normalize_name(record.name):
        if not command.name.strip():
            raise ValidationFailedError("A record's name cannot be empty.")
        old = record.name
        await EntityRepository(scope.session).rename(record, command.name.strip()[:NAME_MAX_LENGTH])
        await rewrite_name(scope.session, record.id, old, record.name)
        messages.append(await hand(ctx, creator, RECORD_RENAMED, ids=[record.id], old=old, new=record.name))
    if command.title is not None:
        record.title = command.title.strip()[:TITLE_MAX_LENGTH] or None
        fields.append("title")
    if command.subtype is not None:
        record.subtype = command.subtype.strip()[:SUBTYPE_MAX_LENGTH] or None
        fields.append("kind")
    if command.description is not None:
        if not command.description.strip():
            raise ValidationFailedError("A record's description cannot be emptied.")
        record.description = command.description.strip()[:ENTITY_TEXT_MAX_LENGTH]
        fields.append("description")
    if command.image_prompt is not None:
        record.image_prompt = command.image_prompt.strip() or None
        fields.append("image prompt")
    fields.extend(region_flags(record, command))
    if not fields and not messages:
        raise ValidationFailedError(f"Nothing to change on {record.name}.")
    if fields:
        messages.append(await hand(ctx, creator, RECORD_EDITED, ids=[record.id], entity=record.name, fields=", ".join(fields)))
    return Effect(" ".join(messages), record.id)


@player_action("thread:open", ActionKind.EDIT_RECORD)
async def open_thread(scope: PlayerScope, command: OpenThread) -> Effect:
    text = command.text.strip()
    if not text:
        raise ValidationFailedError("The story must have a text.")
    epoch = await scope.epoch()
    thread = await open_story(scope.session, text, command.related_ids, epoch)
    if thread is None:
        raise ValidationFailedError("The story must have a text.")
    related = await story_entities(scope.session, thread.id)
    creator = await scope.creator()
    ctx = await scope.context("thread_open")
    message = await hand(ctx, creator, THREAD_OPENED, ids=related, text=text[:THREAD_HEADLINE_LENGTH])
    return Effect(message, created_ids=(thread.id,), values={"thread_id": thread.id})


@player_action("thread:close", ActionKind.EDIT_RECORD)
async def close_thread(scope: PlayerScope, command: CloseThread) -> Effect:
    thread = await scope.session.get(ThreadRow, command.thread_id)
    if thread is None or thread.status is not ThreadStatus.OPEN:
        raise NotFoundError("No such open story.")
    await close_story(scope.session, thread, command.how.strip() or THREAD_DEFAULT_CLOSING, await scope.epoch())
    creator = await scope.creator()
    ctx = await scope.context("thread_close")
    message = await hand(ctx, creator, THREAD_CLOSED, story=thread.id, how=thread.closing_text)
    return Effect(message, values={"thread_id": thread.id})


class AdvanceThread(Command):
    thread_id: int
    entity_id: int


class EditEpoch(Command):
    epoch: int
    name: str | None = None
    narrative: str | None = None


@player_action("thread:advance", ActionKind.EDIT_RECORD)
async def advance_thread(scope: PlayerScope, command: AdvanceThread) -> Effect:
    thread = await scope.session.get(ThreadRow, command.thread_id)
    if thread is None or thread.status is not ThreadStatus.OPEN:
        raise NotFoundError("No such open story.")
    entity = await guards.entity(scope.session, command.entity_id)
    if not await advance_story(scope.session, thread, entity.id, await scope.epoch()):
        raise ValidationFailedError(f"{entity.name} already moved this story forward.")
    message = await hand(await scope.context("thread_advance"), await scope.creator(), THREAD_ADVANCED, story=thread.id, entity=entity.name)
    return Effect(message, entity.id, values={"thread_id": thread.id, "progress": thread.progress})


@player_action("epoch:edit", ActionKind.EDIT_RECORD)
async def edit_epoch(scope: PlayerScope, command: EditEpoch) -> Effect:
    row = await scope.session.get(EpochRow, command.epoch)
    if row is None:
        raise NotFoundError("No such epoch.")
    changed: list[str] = []
    if command.name is not None:
        row.name = command.name.strip()[:ENTITY_TEXT_MAX_LENGTH] or None
        changed.append("name")
    if command.narrative is not None:
        row.narrative = command.narrative.strip() or None
        changed.append("narrative")
    if not changed:
        raise ValidationFailedError("Give a name or a narrative.")
    message = await hand(await scope.context("epoch_edit"), await scope.creator(), EPOCH_EDITED, epoch=row.epoch, fields=", ".join(changed))
    return Effect(message, values={"epoch": row.epoch})


@player_action("fact:add", ActionKind.EDIT_RECORD)
async def add_fact(scope: PlayerScope, command: AddFact) -> Effect:
    subject = await guards.entity(scope.session, command.subject_id)
    relation = command.relation.strip()
    if not relation:
        raise ValidationFailedError("A fact needs a relation.")
    object_text = (command.object_text or "").strip() or None
    if command.object_id is None and object_text is None:
        raise ValidationFailedError("An object is needed.")
    if command.object_id is not None:
        await guards.entity(scope.session, command.object_id)
    fact = await add_manual_fact(scope.session, FactDraft(subject.id, relation, command.object_id, object_text), await scope.epoch())
    return Effect(f"A fact was set: {subject.name} {fact.predicate} {object_text or command.object_id}.", subject.id, values={"fact_id": fact.id})


@player_action("fact:remove", ActionKind.EDIT_RECORD)
async def remove_fact(scope: PlayerScope, command: FactTarget) -> Effect:
    fact = await scope.session.get(CanonFactRow, command.fact_id)
    if fact is None:
        raise NotFoundError("No such fact.")
    if not fact.active:
        raise ValidationFailedError("This fact is already retired.")
    await retract_fact(scope.session, fact.id)
    return Effect("The fact was retired; it is kept as history.", fact.subject_entity_id)


@player_action("belief:edit", ActionKind.EDIT_RECORD)
async def edit_belief(scope: PlayerScope, command: EditBelief) -> Effect:
    people = await guards.entity(scope.session, command.people_id)
    narrative = command.narrative.strip()
    if not narrative:
        raise ValidationFailedError("The people's narrative is required.")
    creator = await scope.creator()
    god_id, guarded = creator.id, guarded_names(creator.name, creator.title)
    if command.son_id is not None:
        son = await guards.son(scope.session, command.son_id)
        god_id, guarded = son.id, guarded_names(son.name, son.title)
    belief = await scope.session.get(FolkBeliefRow, (people.id, god_id))
    epoch = await scope.epoch()
    if belief is None:
        belief = FolkBeliefRow(people_entity_id=people.id, god_node_id=god_id, account=narrative, epoch=epoch)
        scope.session.add(belief)
    given = (command.name or "").strip()[:NAME_MAX_LENGTH]
    belief.local_name = given or belief.local_name or await folk_god_name(Namer(scope.session, scope.rules), scope.rules, people, god_id, guarded)
    belief.account = narrative
    belief.misconception = (command.misconception or "").strip() or None
    belief.epoch = epoch
    await scope.session.flush()
    return Effect(f"{people.name} now tells of {belief.local_name or 'their god'} anew.", people.id)


async def _bond_end(scope: PlayerScope, node_id: int) -> str:
    kind = await NodeRepository(scope.session).kind_of(node_id)
    if kind is None:
        raise NotFoundError("No such bond endpoint.")
    if kind not in BOND_NODE_KINDS:
        raise ValidationFailedError("A bond endpoint must be an entity or a son.")
    return await NodeRepository(scope.session).name_of(node_id) or str(node_id)


@player_action("bond:add", ActionKind.WEAVE_BOND)
async def add_bond(scope: PlayerScope, command: AddBond) -> Effect:
    if command.kind is BondKind.INSIDE:
        raise ValidationFailedError(f'Invalid bond type: {command.kind.value}. "Inside" is location; it changes by moving.')
    if command.kind in DERIVED_BOND_KINDS:
        raise ValidationFailedError(f"{command.kind.value.replace('_', ' ').capitalize()} comes from the record itself; set it on the legend, creed or rite.")
    if command.source_id == command.target_id:
        raise ValidationFailedError("A thing cannot be bonded to itself.")
    first = await _bond_end(scope, command.source_id)
    second = await _bond_end(scope, command.target_id)
    bonds = BondRepository(scope.session)
    if await bonds.active_between(command.source_id, command.target_id, [command.kind]):
        raise ValidationFailedError("This bond already exists.")
    epoch = await scope.epoch()
    bond = await bonds.connect(BondDraft(command.source_id, command.target_id, command.kind, epoch, (command.description or "").strip() or DEFAULT_BOND_TEXT))
    creator = await scope.creator()
    ctx = await scope.context("bond_add")
    message = await hand(ctx, creator, BOND_ADDED, ids=[command.source_id, command.target_id], first=first, second=second, label=bond_spec(command.kind).label)
    return Effect(message, command.source_id, created_ids=(bond.id,))


@player_action("bond:remove", ActionKind.WEAVE_BOND)
async def remove_bond(scope: PlayerScope, command: BondTarget) -> Effect:
    bond = await scope.session.get(BondRow, command.bond_id)
    if bond is None:
        raise NotFoundError("No such bond.")
    if bond.state is not BondState.ACTIVE:
        raise ValidationFailedError("This bond is already broken.")
    if bond.kind is BondKind.INSIDE:
        raise ValidationFailedError('"Inside" is location; move the entity instead of breaking the bond.')
    epoch = await scope.epoch()
    await BondRepository(scope.session).deactivate(bond, epoch, "broken by the god's hand")
    names = NodeRepository(scope.session)
    first = await names.name_of(bond.source_node_id) or str(bond.source_node_id)
    second = await names.name_of(bond.target_node_id) or str(bond.target_node_id)
    creator = await scope.creator()
    ctx = await scope.context("bond_remove")
    message = await hand(
        ctx, creator, BOND_BROKEN, ids=[bond.source_node_id, bond.target_node_id], first=first, second=second, label=bond_spec(bond.kind).label
    )
    return Effect(message, bond.source_node_id)


@player_action("map_note:add", ActionKind.EDIT_RECORD)
async def add_map_note(scope: PlayerScope, command: AddMapNote) -> Effect:
    world = await guards.world(scope.session, command.world_id)
    text = command.text.strip()
    if not text:
        raise ValidationFailedError("A map note needs text.")
    if len(text) > MAP_NOTE_MAX_LENGTH:
        raise ValidationFailedError(f"A map note is at most {MAP_NOTE_MAX_LENGTH} characters.")
    color = (command.color or "").strip() or None
    if color is not None and len(color) > MAP_NOTE_COLOR_MAX_LENGTH:
        raise ValidationFailedError("That colour is not valid.")
    note = MapNoteRow(world_id=world.id, x=command.x, y=command.y, text=text, color=color)
    scope.session.add(note)
    await scope.session.flush()
    return Effect(f"A note was pinned on the map of {world.name}.", world.id, created_ids=(note.id,), values={"note_id": note.id})


@player_action("map_note:remove", ActionKind.EDIT_RECORD)
async def remove_map_note(scope: PlayerScope, command: MapNoteTarget) -> Effect:
    note = await scope.session.get(MapNoteRow, command.note_id)
    if note is None:
        raise NotFoundError("No such map note.")
    world_id = note.world_id
    await scope.session.delete(note)
    await scope.session.flush()
    return Effect("The map note was removed.", world_id)


async def _repoint_bonds(scope: PlayerScope, main: EntityRow, other: EntityRow, epoch: int) -> int:
    moved = 0
    bonds = BondRepository(scope.session)
    for bond in list(await scope.session.scalars(select(BondRow).where(or_(BondRow.source_node_id == other.id, BondRow.target_node_id == other.id)))):
        source = main.id if bond.source_node_id == other.id else bond.source_node_id
        target = main.id if bond.target_node_id == other.id else bond.target_node_id
        if source == target or (bond.state is BondState.ACTIVE and await bonds.active_between(source, target, [bond.kind])):
            await bonds.deactivate(bond, epoch, "merged")
            continue
        bond.source_node_id = source
        bond.target_node_id = target
        moved += 1
    await scope.session.flush()
    return moved


async def _union_marks(scope: PlayerScope, main: EntityRow, other: EntityRow) -> None:
    entities = EntityRepository(scope.session)
    for flag in await entities.flags(other.id):
        await entities.add_flag(main.id, flag)
    for trait in await entities.traits(other.id):
        await entities.add_trait(main.id, trait)
    await entities.add_tags(main.id, await entities.tags(other.id))
    for table in (EntityFlagRow, EntityTraitRow, EntityTagRow):
        for row in await scope.session.scalars(select(table).where(table.entity_id == other.id)):
            await scope.session.delete(row)
    await scope.session.flush()


@player_action("record:merge", ActionKind.MERGE_RECORDS)
async def merge_records(scope: PlayerScope, command: MergeRecords) -> Effect:
    if command.confirm != ConfirmationWord.MERGE:
        raise ValidationFailedError(f"Type {ConfirmationWord.MERGE.value} to confirm the merge.")
    main = await guards.entity(scope.session, command.entity_id)
    other = await guards.entity(scope.session, command.other_id)
    if main.id == other.id:
        raise ValidationFailedError("A record cannot be merged into itself.")
    if main.entity_type is not other.entity_type:
        raise ValidationFailedError(
            f"Only records of the same type merge; {main.name} is {an(main.entity_type.value)}, {other.name} {an(other.entity_type.value)}."
        )
    epoch = await scope.epoch()
    moved = await _repoint_bonds(scope, main, other, epoch)
    for child in list(await scope.session.scalars(select(EntityRow).where(EntityRow.location_id == other.id))):
        child.location_id = main.id if child.id != main.id else None
    await scope.session.execute(update(LexemeRow).where(LexemeRow.language_entity_id == other.id).values(language_entity_id=main.id))
    await scope.session.execute(update(ImageRow).where(ImageRow.target_node_id == other.id).values(target_node_id=main.id, is_cover=False))
    await _union_marks(scope, main, other)
    main.description = (main.description + ALSO_KNOWN_AS.format(other=other.name, description=other.description))[:ENTITY_TEXT_MAX_LENGTH]
    if other.location_id == main.id:
        other.location_id = None
    await EntityRepository(scope.session).set_status(other, EntityStatus.DESTROYED, epoch, f"Merged into {main.name}.")
    creator = await scope.creator()
    ctx = await scope.context("merge")
    message = await tell(ctx, MERGED, ids=[main.id, other.id], creator=creator.name, other=other.name, main=main.name)
    return Effect(message, main.id, values={"bonds_moved": moved})


@player_action("record:favorite", ActionKind.EDIT_RECORD)
async def set_favorite(scope: PlayerScope, command: Favorite) -> Effect:
    record = await guards.entity(scope.session, command.entity_id)
    record.favorite = command.favorite
    return Effect(f"{record.name} {'is now' if command.favorite else 'is no longer'} a favourite.", record.id)


@player_action("record:note", ActionKind.EDIT_RECORD)
async def set_private_note(scope: PlayerScope, command: PrivateNote) -> Effect:
    record = await guards.entity(scope.session, command.entity_id)
    text = command.text.strip()
    if len(text) > PRIVATE_NOTE_MAX_LENGTH:
        raise ValidationFailedError(f"A personal note is at most {PRIVATE_NOTE_MAX_LENGTH} characters.")
    record.private_note = text or None
    return Effect(f"The personal note on {record.name} was {'saved' if text else 'cleared'}.", record.id)
