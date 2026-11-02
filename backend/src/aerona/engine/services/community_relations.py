from dataclasses import dataclass

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.society import community_relation_label
from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunityRelationEventRow, CommunityRelationRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.limits import RELATION_MAX, RELATION_MIN
from aerona.domain.enums.society import CommunityRelationLabel
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import spoken_language
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class RelationEvent:
    epoch: int
    event: str
    delta: int


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


async def initial_relation(session: AsyncSession, rules: Rules, first: int, second: int) -> int:
    relations = rules.diplomacy
    bonds = BondRepository(session)
    value = 0
    first_patron, second_patron = await bonds.patron(first), await bonds.patron(second)
    if first_patron is not None and second_patron is not None:
        value += relations.initial_shared_god if first_patron == second_patron else -relations.initial_different_god
    first_language, second_language = await spoken_language(session, first), await spoken_language(session, second)
    if first_language is not None and second_language is not None and first_language.id == second_language.id:
        value += relations.initial_shared_language
    if await bonds.exists_between(first, second, BondKind.ENEMY):
        value -= relations.initial_enemy
    if await bonds.exists_between(first, second, BondKind.ALLY):
        value += relations.initial_ally
    if await bonds.exists_between(first, second, BondKind.TRADES_WITH):
        value += relations.initial_trade
    if await bonds.exists_between(first, second, BondKind.PAYS_TRIBUTE):
        value -= relations.initial_tribute
    return clamp_int(value, RELATION_MIN, RELATION_MAX)


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


async def _record_event(session: AsyncSession, rules: Rules, row: CommunityRelationRow, *, epoch: int, event: str, delta: int) -> None:
    session.add(CommunityRelationEventRow(entity_a_id=row.entity_a_id, entity_b_id=row.entity_b_id, epoch=epoch, event=event, delta=delta))
    await session.flush()
    pair = and_(CommunityRelationEventRow.entity_a_id == row.entity_a_id, CommunityRelationEventRow.entity_b_id == row.entity_b_id)
    keep = select(CommunityRelationEventRow.id).where(pair).order_by(CommunityRelationEventRow.id.desc()).limit(rules.diplomacy.relation_history_len)
    await session.execute(delete(CommunityRelationEventRow).where(pair, CommunityRelationEventRow.id.not_in(keep)))


async def change_relation(ctx: TickContext, first: int, second: int, delta: float, event: str | None = None) -> int:
    session, rules, epoch = ctx.session, ctx.rules, ctx.epoch
    if first == second:
        return RELATION_MAX
    if delta == 0:
        return await relation(session, rules, first, second)
    row = await _ensure_row(session, rules, first, second)
    if event is not None:
        await _record_event(session, rules, row, epoch=epoch, event=event, delta=round_half_up(delta))
    row.value = clamp_int(row.value + delta, RELATION_MIN, RELATION_MAX)
    await session.flush()
    return row.value


async def set_relation(ctx: TickContext, first: int, second: int, value: int, event: str) -> int:
    session, rules, epoch = ctx.session, ctx.rules, ctx.epoch
    if first == second:
        return RELATION_MAX
    row = await _ensure_row(session, rules, first, second)
    target = clamp_int(value, RELATION_MIN, RELATION_MAX)
    delta = target - row.value
    if delta:
        await _record_event(session, rules, row, epoch=epoch, event=event, delta=delta)
    row.value = target
    await session.flush()
    return row.value


async def start_blood_feud(ctx: TickContext, first: int, second: int, reason: str) -> int:
    session, rules, epoch = ctx.session, ctx.rules, ctx.epoch
    if first == second:
        return RELATION_MAX
    row = await _ensure_row(session, rules, first, second)
    if row.blood_feud_since_epoch is None:
        row.blood_feud_since_epoch = epoch
    return await change_relation(ctx, first, second, -ctx.rules.diplomacy.blood_feud, reason)


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


async def relation_history(session: AsyncSession, first: int, second: int, limit: int) -> tuple[RelationEvent, ...]:
    low, high = pair_key(first, second)
    statement = (
        select(CommunityRelationEventRow)
        .where(CommunityRelationEventRow.entity_a_id == low, CommunityRelationEventRow.entity_b_id == high)
        .order_by(CommunityRelationEventRow.id.desc())
        .limit(limit)
    )
    rows = list(await session.scalars(statement))
    return tuple(RelationEvent(row.epoch, row.event, row.delta) for row in reversed(rows))


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
        history = await relation_history(session, entity_id, other_id, rules.diplomacy.relation_list_history)
        views.append(
            RelationView(other.id, other.name, other.entity_type, row.value, community_relation_label(rules, row.value), row.blood_feud_since_epoch, history)
        )
    return views


async def revert_extreme_relations(session: AsyncSession, rules: Rules) -> int:
    threshold = rules.diplomacy.relation_decay_threshold
    share = rules.diplomacy.relation_decay_pct
    if share <= 0:
        return 0
    statement = select(CommunityRelationRow).where(or_(CommunityRelationRow.value > threshold, CommunityRelationRow.value < -threshold))
    living = set(await session.scalars(select(EntityRow.id).where(EntityRow.status == EntityStatus.CANON)))
    changed = 0
    for row in await session.scalars(statement):
        if row.entity_a_id not in living or row.entity_b_id not in living:
            continue
        if row.value > threshold:
            step = round_half_up((row.value - threshold) * share / PERCENT)
            row.value -= step
        else:
            step = round_half_up((-threshold - row.value) * share / PERCENT)
            row.value += step
        changed += 1 if step else 0
    await session.flush()
    return changed
