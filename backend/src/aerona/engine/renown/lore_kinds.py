from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.discovery import BlueprintRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import SecretRow, TrueNameRow
from aerona.db.tables.powers import PowerSourceRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.discovery import BlueprintSource
from aerona.domain.enums.renown import LoreKind
from aerona.engine.context import TickContext
from aerona.engine.intrigue.secrets import learn
from aerona.engine.primitives.queries import connect

Held = set[tuple[str, int | None]]


@dataclass(frozen=True)
class LoreWay:
    holdings: Callable[[AsyncSession, int], Awaitable[Held]]
    holders: Callable[[AsyncSession, int | None], Awaitable[int]]
    grant: Callable[[TickContext, EntityRow, int | None], Awaitable[bool]]


async def names_held(session: AsyncSession, holder_id: int) -> Held:
    return {("true_name", row.bearer_node_id) for row in await session.scalars(select(TrueNameRow)) if holder_id in (row.known_by or [])}


async def name_holders(session: AsyncSession, subject: int | None) -> int:
    row = await session.get(TrueNameRow, subject) if subject is not None else None
    return len(row.known_by or []) if row is not None else 0


async def grant_name(_ctx: TickContext, holder: EntityRow, subject: int | None) -> bool:
    row = await _ctx.session.get(TrueNameRow, subject) if subject is not None else None
    if row is None or holder.id in (row.known_by or []) or "known_by" in row.locked:
        return False
    row.known_by = [*(row.known_by or []), holder.id]
    return True


async def weaknesses_held(session: AsyncSession, holder_id: int) -> Held:
    return {
        ("weakness", row.id) for row in await session.scalars(select(SecretRow).where(SecretRow.exposed_epoch.is_(None))) if holder_id in (row.known_by or [])
    }


async def weakness_holders(session: AsyncSession, subject: int | None) -> int:
    row = await session.get(SecretRow, subject) if subject is not None else None
    return len(row.known_by or []) if row is not None else 0


async def grant_weakness(ctx: TickContext, holder: EntityRow, subject: int | None) -> bool:
    row = await ctx.session.get(SecretRow, subject) if subject is not None else None
    return row is not None and await learn(ctx, row, holder.id)


async def patterns_held(session: AsyncSession, holder_id: int) -> Held:
    return {("pattern", row.id) for row in await session.scalars(select(BlueprintRow).where(BlueprintRow.holder_node_id == holder_id))}


async def pattern_holders(session: AsyncSession, subject: int | None) -> int:
    row = await session.get(BlueprintRow, subject) if subject is not None else None
    if row is None:
        return 0
    return int(await session.scalar(select(func.count()).select_from(BlueprintRow).where(BlueprintRow.name == row.name)) or 0)


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


WIDER_LORE: Mapping[LoreKind, LoreWay] = {
    LoreKind.TRUE_NAME: LoreWay(names_held, name_holders, grant_name),
    LoreKind.WEAKNESS: LoreWay(weaknesses_held, weakness_holders, grant_weakness),
    LoreKind.PATTERN: LoreWay(patterns_held, pattern_holders, grant_pattern),
    LoreKind.SOURCE: LoreWay(sources_held, source_holders, grant_source),
}
