from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mind import MEMORIES
from aerona.catalog.society import community_relation_label
from aerona.constants.schema import SINGLETON_ID
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.limits import RELATION_MAX, RELATION_MIN
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.society import CommunityRelationLabel
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.mind.book import ValueIndex
from aerona.engine.mind.memories import memories_between, remember, strength_of
from aerona.engine.mind.opinion import OpinionContext, pair_relation
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules

SET_PASSES = 3


@dataclass(frozen=True)
class RelationEvent:
    epoch: int
    event: str
    delta: int
    kind: MemoryKind
    holder_id: int


@dataclass(frozen=True)
class RelationView:
    entity_id: int
    name: str
    entity_type: EntityType
    value: int
    label: CommunityRelationLabel
    blood_feud_since_epoch: int | None
    history: tuple[RelationEvent, ...]


def pair_key(first: int, second: int) -> tuple[int, int]:
    return (first, second) if first < second else (second, first)


async def cosmos_epoch(session: AsyncSession) -> int:
    cosmos = await session.get(CosmosRow, SINGLETON_ID)
    return cosmos.epoch if cosmos is not None else 0


async def initial_relation(session: AsyncSession, rules: Rules, first: int, second: int) -> int:
    return await pair_relation(session, rules, await cosmos_epoch(session), first, second)


async def _row(session: AsyncSession, first: int, second: int) -> CommunityRelationRow | None:
    return await session.get(CommunityRelationRow, pair_key(first, second))


async def _ensure_row(session: AsyncSession, rules: Rules, first: int, second: int) -> CommunityRelationRow:
    row = await _row(session, first, second)
    if row is None:
        low, high = pair_key(first, second)
        row = CommunityRelationRow(entity_a_id=low, entity_b_id=high, value=await initial_relation(session, rules, first, second))
        session.add(row)
        await session.flush()
    return row


async def remember_relation(session: AsyncSession, rules: Rules, first: int, second: int) -> int:
    if first == second:
        return RELATION_MAX
    return (await _ensure_row(session, rules, first, second)).value


async def relation(session: AsyncSession, rules: Rules, first: int, second: int) -> int:
    if first == second:
        return RELATION_MAX
    row = await _row(session, first, second)
    if row is not None:
        return row.value
    return await initial_relation(session, rules, first, second)


async def refresh_relation(session: AsyncSession, rules: Rules, epoch: int, first: int, second: int) -> int:
    if first == second:
        return RELATION_MAX
    row = await _ensure_row(session, rules, first, second)
    row.value = await pair_relation(session, rules, epoch, first, second)
    await session.flush()
    return row.value


async def change_relation(
    ctx: TickContext,
    first: int,
    second: int,
    delta: float,
    kind: MemoryKind,
    *,
    note: str | None = None,
    reverse: MemoryKind | None = None,
    event_id: int | None = None,
) -> int:
    session, rules, epoch = ctx.session, ctx.rules, ctx.epoch
    if first == second:
        return RELATION_MAX
    if delta == 0:
        return await relation(session, rules, first, second)
    await _ensure_row(session, rules, first, second)
    await remember(session, rules, holder_id=first, subject_id=second, kind=kind, magnitude=delta, epoch=epoch, note=note, event_id=event_id)
    await remember(session, rules, holder_id=second, subject_id=first, kind=reverse or kind, magnitude=delta, epoch=epoch, note=note, event_id=event_id)
    return await refresh_relation(session, rules, epoch, first, second)


async def set_relation(ctx: TickContext, first: int, second: int, value: int, note: str) -> int:
    session, rules, epoch = ctx.session, ctx.rules, ctx.epoch
    if first == second:
        return RELATION_MAX
    target = clamp_int(value, RELATION_MIN, RELATION_MAX)
    current = await refresh_relation(session, rules, epoch, first, second)
    for _ in range(SET_PASSES):
        gap = target - current
        if not gap:
            break
        step = max(RELATION_MIN, min(RELATION_MAX, gap))
        for holder, subject in ((first, second), (second, first)):
            await remember(
                session,
                rules,
                holder_id=holder,
                subject_id=subject,
                kind=MemoryKind.DIVINE_WILL,
                magnitude=step,
                epoch=epoch,
                note=note,
                decay_pct=0,
                forced=True,
                merge=False,
            )
        current = await refresh_relation(session, rules, epoch, first, second)
    return current


async def start_blood_feud(ctx: TickContext, first: int, second: int, reason: str) -> int:
    session, rules, epoch = ctx.session, ctx.rules, ctx.epoch
    if first == second:
        return RELATION_MAX
    row = await _ensure_row(session, rules, first, second)
    if row.blood_feud_since_epoch is None:
        row.blood_feud_since_epoch = epoch
    decay = rules.memory.feud_decay_pct
    for holder, subject in ((first, second), (second, first)):
        await remember(
            session,
            rules,
            holder_id=holder,
            subject_id=subject,
            kind=MemoryKind.KILLED_KIN,
            magnitude=-rules.diplomacy.blood_feud,
            epoch=epoch,
            note=reason,
            decay_pct=decay,
        )
    return await refresh_relation(session, rules, epoch, first, second)


async def end_blood_feud(session: AsyncSession, first: int, second: int) -> bool:
    row = await _row(session, first, second)
    if row is None or row.blood_feud_since_epoch is None:
        return False
    row.blood_feud_since_epoch = None
    await session.flush()
    return True


async def has_blood_feud(session: AsyncSession, first: int, second: int) -> bool:
    row = await _row(session, first, second)
    return row is not None and row.blood_feud_since_epoch is not None


async def blood_feud_pairs(session: AsyncSession) -> set[tuple[int, int]]:
    rows = await session.execute(
        select(CommunityRelationRow.entity_a_id, CommunityRelationRow.entity_b_id).where(CommunityRelationRow.blood_feud_since_epoch.is_not(None))
    )
    return {(first, second) for first, second in rows}


def event_of(row: MemoryRow, epoch: int) -> RelationEvent:
    return RelationEvent(row.epoch, row.note or MEMORIES[row.kind].label, round_half_up(strength_of(row, epoch)), row.kind, row.holder_node_id)


async def relation_history(session: AsyncSession, first: int, second: int, limit: int | None = None) -> tuple[RelationEvent, ...]:
    epoch = await cosmos_epoch(session)
    rows = sorted(await memories_between(session, first, second), key=lambda row: (row.epoch, row.id))
    events = tuple(event_of(row, epoch) for row in rows)
    return events if limit is None else events[-limit:]


async def relation_list(session: AsyncSession, rules: Rules, entity_id: int, limit: int | None = None) -> list[RelationView]:
    size = limit if limit is not None else rules.server.community_relations_shown
    statement = select(CommunityRelationRow).where(or_(CommunityRelationRow.entity_a_id == entity_id, CommunityRelationRow.entity_b_id == entity_id))
    rows = sorted(await session.scalars(statement), key=lambda row: (-abs(row.value), row.entity_a_id, row.entity_b_id))
    views: list[RelationView] = []
    for row in rows:
        if len(views) >= size:
            break
        other_id = row.entity_b_id if row.entity_a_id == entity_id else row.entity_a_id
        other = await session.get(EntityRow, other_id)
        if other is None or other.status is not EntityStatus.CANON:
            continue
        history = await relation_history(session, entity_id, other_id, rules.opinion.listed_memories)
        views.append(
            RelationView(other.id, other.name, other.entity_type, row.value, community_relation_label(rules, row.value), row.blood_feud_since_epoch, history)
        )
    return views


async def refresh_relations(session: AsyncSession, rules: Rules, epoch: int) -> int:
    living = set(await session.scalars(select(EntityRow.id).where(EntityRow.status == EntityStatus.CANON)))
    rows = [row for row in await session.scalars(select(CommunityRelationRow)) if row.entity_a_id in living and row.entity_b_id in living]
    if not rows:
        return 0
    values = await ValueIndex.load(session)
    await lend_settlement_values(session, values, {node for row in rows for node in (row.entity_a_id, row.entity_b_id)})
    context = await OpinionContext.load(session, rules, epoch, [node for row in rows for node in (row.entity_a_id, row.entity_b_id)], values)
    changed = 0
    for row in rows:
        value = context.relation(row.entity_a_id, row.entity_b_id)
        if value != row.value:
            row.value = value
            changed += 1
    await session.flush()
    return changed


async def lend_settlement_values(session: AsyncSession, values: ValueIndex, nodes: set[int]) -> None:
    for node in sorted(nodes):
        if node in values.vectors:
            continue
        entity = await session.get(EntityRow, node)
        if entity is None or entity.entity_type is not EntityType.SETTLEMENT:
            continue
        people = await people_of(session, entity)
        if people is not None:
            values.lend(node, people.id)
