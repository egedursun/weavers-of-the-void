from collections import Counter

from sqlalchemy import and_, func, or_, select

from aerona.agents.context.entity_line import line_items
from aerona.agents.context.recent_chronicle import prompt_text
from aerona.agents.context.scope import Scope
from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleEntityRow, FolkBeliefRow, MessageRow, ThreadLinkRow, ThreadRow
from aerona.db.tables.lore import ChronicleRow as ChronicleRecord
from aerona.db.tables.node import NodeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind, ThreadStatus
from aerona.domain.enums.entity import EntityStatus
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import FolkBeliefLine, MemoryCreation, MemoryWord, RepeatBucket, SonMemoryContext
from aerona.prompts.contexts.common import ChronicleRow, NamedRecord, WorldItem


async def memory_words(scope: Scope, son: SonRow) -> list[MemoryWord]:
    limit = scope.rules.context.memory_messages_count
    rows = list(
        await scope.session.execute(
            select(MessageRow, NodeRow.name)
            .join(NodeRow, NodeRow.id == MessageRow.sender_node_id)
            .where(MessageRow.recipient_node_id == son.id)
            .order_by(MessageRow.id.desc())
            .limit(limit)
        )
    )
    return [
        MemoryWord(age=message.epoch, from_father=message.sender_node_id == scope.creator.id, sender=name, intent_label=message.intent.value, text=message.text)
        for message, name in reversed(rows)
    ]


async def memory_creations(scope: Scope, son: SonRow) -> tuple[list[MemoryCreation], int, list[RepeatBucket]]:
    context = scope.rules.context
    total = int(await scope.session.scalar(select(func.count()).select_from(EntityRow).where(EntityRow.creator_son_id == son.id)) or 0)
    recent = list(
        await scope.session.scalars(
            select(EntityRow)
            .where(EntityRow.creator_son_id == son.id)
            .order_by(EntityRow.id.desc())
            .limit(max(context.memory_creations_count, context.repeat_window))
        )
    )
    shown = recent[: context.memory_creations_count]
    items = await line_items(scope.session, shown)
    creations = [
        MemoryCreation(
            entity=item,
            other_world=scope.world_name(entity.world_id) if scope.multi_world and entity.world_id != son.current_world_id else None,
            fate_note=entity.fate_note if entity.status is EntityStatus.REJECTED else None,
        )
        for entity, item in zip(shown, items, strict=True)
    ]
    buckets = Counter(
        f"{ENTITY_TYPES[entity.entity_type].label}/{entity.subtype}" if entity.subtype else ENTITY_TYPES[entity.entity_type].label
        for entity in recent[: context.repeat_window]
    )
    repeats = [RepeatBucket(label=label, count=count) for label, count in buckets.items() if count >= context.repeat_warning_threshold]
    return list(reversed(creations)), total, repeats


async def memory_worshippers(scope: Scope, son: SonRow) -> tuple[list[NamedRecord], int]:
    rows = list(
        await scope.session.execute(
            select(EntityRow.id, EntityRow.name)
            .join(BondRow, BondRow.source_node_id == EntityRow.id)
            .where(
                BondRow.target_node_id == son.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, EntityRow.status == EntityStatus.CANON
            )
            .order_by(EntityRow.id)
        )
    )
    limit = scope.rules.context.memory_named_worshippers
    return [NamedRecord(id=entity_id, name=name) for entity_id, name in rows[:limit]], max(0, len(rows) - limit)


async def recollections(scope: Scope, son: SonRow) -> list[ChronicleRow]:
    rows = await scope.session.scalars(
        select(ChronicleRecord)
        .where(ChronicleRecord.son_id == son.id, ChronicleRecord.kind != ChronicleKind.CREATION, ChronicleRecord.visible.is_(True))
        .order_by(ChronicleRecord.id.desc())
        .limit(scope.rules.context.memory_recollections_count)
    )
    return [ChronicleRow(age=row.epoch, text=prompt_text(row.text)) for row in reversed(list(rows))]


async def about_son(scope: Scope, son: SonRow) -> list[ChronicleRow]:
    created = select(EntityRow.id).where(EntityRow.creator_son_id == son.id)
    rows = await scope.session.scalars(
        select(ChronicleRecord)
        .join(ChronicleEntityRow, ChronicleEntityRow.chronicle_id == ChronicleRecord.id)
        .where(
            ChronicleEntityRow.entity_id.in_(created),
            ChronicleRecord.visible.is_(True),
            or_(ChronicleRecord.son_id.is_(None), ChronicleRecord.son_id != son.id),
        )
        .distinct()
        .order_by(ChronicleRecord.id.desc())
        .limit(scope.rules.context.memory_about_count)
    )
    return [ChronicleRow(age=row.epoch, text=prompt_text(row.text)) for row in reversed(list(rows))]


async def folk_beliefs(scope: Scope, son: SonRow) -> list[FolkBeliefLine]:
    rows = await scope.session.execute(
        select(FolkBeliefRow, EntityRow.name).join(EntityRow, EntityRow.id == FolkBeliefRow.people_entity_id).where(and_(FolkBeliefRow.god_node_id == son.id))
    )
    return [FolkBeliefLine(people=people, name=belief.local_name or son.name, story=belief.account) for belief, people in rows]


async def closed_since(scope: Scope, son: SonRow, since: int) -> list[str]:
    created = select(EntityRow.id).where(EntityRow.creator_son_id == son.id)
    rows = await scope.session.scalars(
        select(ThreadRow.closing_text)
        .join(ThreadLinkRow, ThreadLinkRow.thread_id == ThreadRow.id)
        .where(
            ThreadRow.status == ThreadStatus.CLOSED, ThreadRow.closed_epoch >= since, ThreadLinkRow.entity_id.in_(created), ThreadRow.closing_text.is_not(None)
        )
        .distinct()
        .order_by(ThreadRow.closed_epoch.desc())
        .limit(scope.rules.context.plan_closed_stories)
    )
    limit = scope.rules.context.plan_closed_chars
    return [text[:limit] for text in rows if text]


async def son_memory_context(scope: Scope, son: SonRow, full: bool = False) -> SonMemoryContext:
    creations, total, repeats = await memory_creations(scope, son)
    worshippers, extra = await memory_worshippers(scope, son)
    world = scope.worlds.get(son.current_world_id) if son.current_world_id is not None and scope.multi_world else None
    years = scope.epoch - son.plan_epoch if son.plan_epoch is not None else None
    closed = await closed_since(scope, son, son.plan_epoch) if son.plan and son.plan_epoch is not None else []
    return SonMemoryContext(
        rules=scope.rules,
        full=full,
        plan=son.plan,
        plan_age=son.plan_epoch,
        plan_years=years,
        plan_stale=years is not None and (years >= scope.rules.context.plan_stale_epochs or bool(closed)),
        closed_since_plan=closed,
        words=await memory_words(scope, son),
        creations=creations,
        creations_total=total,
        current_world=WorldItem(id=world.id, name=world.name) if world is not None else None,
        repeats=repeats,
        worshippers=worshippers,
        extra_worshippers=extra,
        recollections=await recollections(scope, son),
        about=await about_son(scope, son),
        beliefs=await folk_beliefs(scope, son),
    )


async def son_memory(scope: Scope, son: SonRow, full: bool = False) -> str:
    return render(PromptId.SON_MEMORY, await son_memory_context(scope, son, full))
