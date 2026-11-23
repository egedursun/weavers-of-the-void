from collections import Counter
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.read_memo import memoized
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.discovery import BlueprintRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import SecretRow, TrueNameRow
from aerona.db.tables.powers import PowerSourceRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.discovery import BlueprintSource
from aerona.domain.enums.knowledge import KnowledgeKind
from aerona.engine.context import TickContext
from aerona.engine.intrigue.secrets import learn
from aerona.engine.primitives.queries import connect

Held = set[tuple[str, int | None]]
HeldIndex = Mapping[int, frozenset[tuple[str, int | None]]]


@dataclass(frozen=True)
class LoreWay:
    holdings: Callable[[AsyncSession, int], Awaitable[Held]]
    holders: Callable[[AsyncSession, int | None], Awaitable[int]]
    grant: Callable[[TickContext, EntityRow, int | None], Awaitable[bool]]


def by_holder(found: dict[int, set[tuple[str, int | None]]]) -> HeldIndex:
    return {holder: frozenset(items) for holder, items in found.items()}


@memoized(TrueNameRow)
async def name_index(session: AsyncSession) -> HeldIndex:
    found: dict[int, set[tuple[str, int | None]]] = {}
    for bearer, known in await session.execute(select(TrueNameRow.bearer_node_id, TrueNameRow.known_by)):
        for holder in known or []:
            found.setdefault(holder, set()).add(("true_name", bearer))
    return by_holder(found)


async def names_held(session: AsyncSession, holder_id: int) -> Held:
    return set((await name_index(session)).get(holder_id, frozenset()))


async def name_holders(session: AsyncSession, subject: int | None) -> int:
    row = await session.get(TrueNameRow, subject) if subject is not None else None
    return len(row.known_by or []) if row is not None else 0


async def grant_name(_ctx: TickContext, holder: EntityRow, subject: int | None) -> bool:
    row = await _ctx.session.get(TrueNameRow, subject) if subject is not None else None
    if row is None or holder.id in (row.known_by or []) or "known_by" in row.locked:
        return False
    row.known_by = [*(row.known_by or []), holder.id]
    return True


@memoized(SecretRow)
async def weakness_index(session: AsyncSession) -> HeldIndex:
    found: dict[int, set[tuple[str, int | None]]] = {}
    for secret, known in await session.execute(select(SecretRow.id, SecretRow.known_by).where(SecretRow.exposed_epoch.is_(None))):
        for holder in known or []:
            found.setdefault(holder, set()).add(("weakness", secret))
    return by_holder(found)


async def weaknesses_held(session: AsyncSession, holder_id: int) -> Held:
    return set((await weakness_index(session)).get(holder_id, frozenset()))


async def weakness_holders(session: AsyncSession, subject: int | None) -> int:
    row = await session.get(SecretRow, subject) if subject is not None else None
    return len(row.known_by or []) if row is not None else 0


async def grant_weakness(ctx: TickContext, holder: EntityRow, subject: int | None) -> bool:
    row = await ctx.session.get(SecretRow, subject) if subject is not None else None
    return row is not None and await learn(ctx, row, holder.id)


@memoized(BlueprintRow)
async def pattern_index(session: AsyncSession) -> HeldIndex:
    found: dict[int, set[tuple[str, int | None]]] = {}
    for pattern, holder in await session.execute(select(BlueprintRow.id, BlueprintRow.holder_node_id)):
        found.setdefault(holder, set()).add(("pattern", pattern))
    return by_holder(found)


@memoized(BlueprintRow)
async def pattern_names(session: AsyncSession) -> Counter[str]:
    return Counter(await session.scalars(select(BlueprintRow.name)))


async def patterns_held(session: AsyncSession, holder_id: int) -> Held:
    return set((await pattern_index(session)).get(holder_id, frozenset()))


async def pattern_holders(session: AsyncSession, subject: int | None) -> int:
    row = await session.get(BlueprintRow, subject) if subject is not None else None
    if row is None:
        return 0
    return (await pattern_names(session))[row.name]


async def grant_pattern(ctx: TickContext, holder: EntityRow, subject: int | None) -> bool:
    row = await ctx.session.get(BlueprintRow, subject) if subject is not None else None
    if row is None or row.holder_node_id == holder.id:
        return False
    copy = BlueprintRow(
        name=row.name, kind=row.kind, subject=row.subject, holder_node_id=holder.id, origin_node_id=row.holder_node_id, source=BlueprintSource.TRADED
    )
    copy.quality, copy.since_epoch, copy.licensed_to, copy.locked = row.quality, ctx.epoch, [], []
    ctx.session.add(copy)
    return True


async def sources_held(session: AsyncSession, holder_id: int) -> Held:
    scopes = select(PowerSourceRow.scope_node_id).where(PowerSourceRow.scope_node_id.is_not(None))
    known = select(BondRow.target_node_id).where(
        BondRow.source_node_id == holder_id, BondRow.kind == BondKind.KNOWS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(scopes)
    )
    return {("source", scope) for scope in await session.scalars(known)}


async def source_holders(session: AsyncSession, subject: int | None) -> int:
    if subject is None:
        return 0
    query = (
        select(func.count()).select_from(BondRow).where(BondRow.target_node_id == subject, BondRow.kind == BondKind.KNOWS, BondRow.state == BondState.ACTIVE)
    )
    return int(await session.scalar(query) or 0)


async def grant_source(ctx: TickContext, holder: EntityRow, subject: int | None) -> bool:
    if subject is None:
        return False
    return await connect(ctx.session, holder.id, subject, BondKind.KNOWS, ctx.epoch, description="told where power wells up") is not None


WIDER_LORE: Mapping[KnowledgeKind, LoreWay] = {
    KnowledgeKind.TRUE_NAME: LoreWay(names_held, name_holders, grant_name),
    KnowledgeKind.WEAKNESS: LoreWay(weaknesses_held, weakness_holders, grant_weakness),
    KnowledgeKind.PATTERN: LoreWay(patterns_held, pattern_holders, grant_pattern),
    KnowledgeKind.SOURCE: LoreWay(sources_held, source_holders, grant_source),
}
