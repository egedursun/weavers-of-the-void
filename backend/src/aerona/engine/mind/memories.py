from dataclasses import dataclass

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mind import MEMORIES
from aerona.constants.units import PERCENT
from aerona.db.key_index import index_spec, keyed_rows
from aerona.db.record_context import current_scope
from aerona.db.repositories.chronicle import incident_for
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.write_guard import held, write_blocked
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.limits import RELATION_MAX, RELATION_MIN
from aerona.domain.enums.mind import MemoryKind, TraitEffect
from aerona.engine.mind.book import MEMORIES_KEY, effect_of, locked_for, scaled_by
from aerona.engine.mortal.kin import children_of as typed_children
from aerona.engine.mortal.kin import close_kin_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds, living_entity
from aerona.rules.registry import Rules

MEMORY_LOCK = "memories"
PHASE_PREFIX = "phase."


@dataclass(frozen=True)
class Remembered:
    row: MemoryRow
    strength: float


def strength_of(row: MemoryRow, epoch: int) -> float:
    age = max(0, epoch - row.epoch)
    return row.magnitude * (1 - row.decay_pct / PERCENT) ** age


async def default_decay(session: AsyncSession, rules: Rules, holder_id: int, kind: MemoryKind) -> int:
    seated = await session.get(MindProfileRow, holder_id)
    if seated is not None and seated.perfect_recall:
        return 0
    base = MEMORIES[kind].decay_pct * rules.memory.decay_scale_pct / PERCENT
    return clamp_int(base * scaled_by(await effect_of(session, holder_id, TraitEffect.MEMORY_DECAY, rules.traits.effect_scale_pct)), 0, PERCENT)


MEMORY_PAIRS = index_spec(MemoryRow, "holder_node_id", "subject_node_id")


async def same_memory(session: AsyncSession, holder_id: int, subject_id: int, kind: MemoryKind, *, epoch: int, inherited_from: int | None) -> MemoryRow | None:
    pairs = await keyed_rows(session, MEMORY_PAIRS)
    if pairs is not None:
        return next(
            (
                row
                for row in sorted(pairs.rows.get((holder_id, subject_id), []), key=lambda row: row.id)
                if row.kind == kind and row.epoch == epoch and row.inherited_from_node_id == inherited_from
            ),
            None,
        )
    statement = select(MemoryRow).where(
        MemoryRow.holder_node_id == holder_id,
        MemoryRow.subject_node_id == subject_id,
        MemoryRow.kind == kind,
        MemoryRow.epoch == epoch,
        MemoryRow.inherited_from_node_id.is_(None) if inherited_from is None else MemoryRow.inherited_from_node_id == inherited_from,
    )
    return await session.scalar(statement.limit(1))


async def remember(
    session: AsyncSession,
    rules: Rules,
    *,
    holder_id: int,
    subject_id: int,
    kind: MemoryKind,
    magnitude: float,
    epoch: int,
    note: str | None = None,
    event_id: int | None = None,
    decay_pct: int | None = None,
    inherited_from: int | None = None,
    forced: bool = False,
    merge: bool = True,
    step_id: int | None = None,
) -> MemoryRow | None:
    size = clamp_int(magnitude, RELATION_MIN, RELATION_MAX)
    if holder_id == subject_id or size == 0 or write_blocked(holder_id, MEMORIES_KEY):
        return None
    if not forced and await locked_for(session, holder_id, MEMORY_LOCK):
        return None
    existing = await same_memory(session, holder_id, subject_id, kind, epoch=epoch, inherited_from=inherited_from) if merge else None
    if existing is not None:
        existing.magnitude = clamp_int(existing.magnitude + size, RELATION_MIN, RELATION_MAX)
        if note:
            existing.note = note
        return existing
    decay = decay_pct if decay_pct is not None else await default_decay(session, rules, holder_id, kind)
    row = MemoryRow(
        holder_node_id=holder_id,
        subject_node_id=subject_id,
        kind=kind,
        magnitude=size,
        decay_pct=clamp_int(decay, 0, PERCENT),
        epoch=epoch,
        note=note,
        event_entity_id=event_id,
        incident_id=remembered_incident() or incident_for(session, holder_id, epoch) or incident_for(session, subject_id, epoch)
        if inherited_from is None
        else None,
        step_id=step_id if step_id is not None else remembered_step() if inherited_from is None else None,
        inherited_from_node_id=inherited_from,
    )
    session.add(row)
    await session.flush()
    return row


def remembered_incident() -> int | None:
    scope = current_scope()
    while scope is not None:
        if scope.incident_id is not None and not scope.key.startswith(PHASE_PREFIX):
            return scope.incident_id
        scope = scope.parent
    return None


def remembered_step() -> int | None:
    scope = current_scope()
    while scope is not None:
        if scope.step_id is not None:
            return scope.step_id
        scope = scope.parent
    return None


async def memories_about(session: AsyncSession, holder_id: int, subject_id: int) -> list[MemoryRow]:
    pairs = await keyed_rows(session, MEMORY_PAIRS)
    if pairs is not None:
        return sorted(pairs.rows.get((holder_id, subject_id), []), key=lambda row: (row.epoch, row.id))
    statement = select(MemoryRow).where(MemoryRow.holder_node_id == holder_id, MemoryRow.subject_node_id == subject_id)
    return list(await session.scalars(statement.order_by(MemoryRow.epoch, MemoryRow.id)))


async def memories_between(session: AsyncSession, first: int, second: int) -> list[MemoryRow]:
    statement = select(MemoryRow).where(
        or_(
            (MemoryRow.holder_node_id == first) & (MemoryRow.subject_node_id == second),
            (MemoryRow.holder_node_id == second) & (MemoryRow.subject_node_id == first),
        )
    )
    return list(await session.scalars(statement.order_by(MemoryRow.epoch, MemoryRow.id)))


async def memories_of(session: AsyncSession, holder_id: int) -> list[MemoryRow]:
    statement = select(MemoryRow).where(MemoryRow.holder_node_id == holder_id)
    return list(await session.scalars(statement.order_by(MemoryRow.epoch, MemoryRow.id)))


async def strongest(session: AsyncSession, holder_id: int, epoch: int, count: int | None = None) -> list[Remembered]:
    found = [Remembered(row, strength_of(row, epoch)) for row in await memories_of(session, holder_id)]
    found.sort(key=lambda item: (-abs(item.strength), -item.row.epoch, item.row.id))
    return found if count is None else found[:count]


async def forget_faded(session: AsyncSession, rules: Rules, epoch: int) -> int:
    floor = rules.memory.forget_below
    faded = [row.id for row in await session.scalars(select(MemoryRow)) if abs(strength_of(row, epoch)) < floor and not held(row.holder_node_id)]
    if faded:
        await session.execute(delete(MemoryRow).where(MemoryRow.id.in_(faded)))
        await session.flush()
    return len(faded)


async def kin_of(session: AsyncSession, mortal_id: int) -> list[EntityRow]:
    ids = await close_kin_of(session, mortal_id)
    kin: list[EntityRow] = []
    for node_id in dict.fromkeys(ids):
        found = await living_entity(session, node_id)
        if found is not None and found.entity_type is EntityType.MORTAL:
            kin.append(found)
    return kin


async def children_of(session: AsyncSession, mortal_id: int) -> list[EntityRow]:
    children: list[EntityRow] = []
    for child_id in await typed_children(session, mortal_id):
        found = await living_entity(session, child_id)
        if found is not None and found.entity_type is EntityType.MORTAL:
            children.append(found)
    return children


async def inherit_memories(session: AsyncSession, rules: Rules, dead: EntityRow, heirs: list[int], epoch: int) -> int:
    settings = rules.memory
    passed = 0
    legacy = [item for item in await strongest(session, dead.id, epoch, settings.inherit_top) if MEMORIES[item.row.kind].inherited]
    for heir in dict.fromkeys(heirs):
        if heir == dead.id:
            continue
        for item in legacy:
            if item.row.subject_node_id == heir:
                continue
            size = item.strength * settings.inherit_pct / PERCENT
            if abs(size) < settings.forget_below:
                continue
            await remember(
                session,
                rules,
                holder_id=heir,
                subject_id=item.row.subject_node_id,
                kind=item.row.kind,
                magnitude=size,
                epoch=epoch,
                note=item.row.note,
                decay_pct=item.row.decay_pct,
                inherited_from=dead.id,
            )
            passed += 1
    return passed


async def ruled_by(session: AsyncSession, mortal_id: int) -> list[int]:
    return [bond.target_node_id for bond in await active_bonds(session, [BondKind.RULES], sources=[mortal_id])]


async def realm_mourns(session: AsyncSession, rules: Rules, dead: EntityRow, ruled: list[int], epoch: int) -> int:
    formed = 0
    share = rules.memory.ruler_people_pct
    for item in await strongest(session, dead.id, epoch, rules.memory.inherit_top):
        if not MEMORIES[item.row.kind].inherited:
            continue
        size = item.strength * share / PERCENT
        if abs(size) < rules.memory.forget_below:
            continue
        for community in ruled:
            if community != item.row.subject_node_id and await remember(
                session,
                rules,
                holder_id=community,
                subject_id=item.row.subject_node_id,
                kind=item.row.kind,
                magnitude=size,
                epoch=epoch,
                note=item.row.note,
                inherited_from=dead.id,
            ):
                formed += 1
    return formed


async def grieve(session: AsyncSession, rules: Rules, dead: EntityRow, killer_id: int, *, ruled: list[int], epoch: int) -> int:
    formed = 0
    grief = rules.memory.killed_kin_magnitude
    mourners: list[tuple[int, float]] = [(relative.id, float(grief)) for relative in await kin_of(session, dead.id)]
    mourners += [(community, grief * rules.memory.ruler_people_pct / PERCENT) for community in ruled]
    for holder, size in mourners:
        if holder != killer_id and await remember(
            session, rules, holder_id=holder, subject_id=killer_id, kind=MemoryKind.KILLED_KIN, magnitude=-size, epoch=epoch, note=dead.name
        ):
            formed += 1
    return formed


async def mourn(session: AsyncSession, rules: Rules, dead: EntityRow, killer_id: int | None, epoch: int) -> int:
    heirs = [child.id for child in await children_of(session, dead.id)]
    formed = await inherit_memories(session, rules, dead, heirs, epoch)
    ruled = await ruled_by(session, dead.id)
    if ruled:
        formed += await realm_mourns(session, rules, dead, ruled, epoch)
    if killer_id is not None and killer_id != dead.id:
        formed += await grieve(session, rules, dead, killer_id, ruled=ruled, epoch=epoch)
    return formed
