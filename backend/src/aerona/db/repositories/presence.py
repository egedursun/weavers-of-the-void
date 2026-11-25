from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.authorship import mine, visible
from aerona.db.tables.presence import PresenceEventRow, PresenceExchangeRow, PresenceSessionRow
from aerona.domain.enums.presence import PresenceEventKind, PresenceExchangeStatus, PresenceRecord, PresenceStatus

FIRST_ORDINAL = 1
FINISHED_EXCHANGES = frozenset({PresenceExchangeStatus.DONE, PresenceExchangeStatus.FAILED, PresenceExchangeStatus.CANCELLED})


async def open_session_of(session: AsyncSession, node_id: int) -> PresenceSessionRow | None:
    return await session.scalar(
        select(PresenceSessionRow)
        .where(PresenceSessionRow.node_id == node_id, PresenceSessionRow.status == PresenceStatus.OPEN, mine(PresenceSessionRow.author_account_id))
        .order_by(PresenceSessionRow.id.desc())
        .limit(1)
    )


async def open_sessions(session: AsyncSession, node_ids: Sequence[int]) -> dict[int, int]:
    if not node_ids:
        return {}
    rows = await session.execute(
        select(PresenceSessionRow.node_id, PresenceSessionRow.id)
        .where(PresenceSessionRow.node_id.in_(node_ids), PresenceSessionRow.status == PresenceStatus.OPEN, mine(PresenceSessionRow.author_account_id))
        .order_by(PresenceSessionRow.id)
    )
    return {node_id: session_id for node_id, session_id in rows}


async def kept_sessions(session: AsyncSession, node_id: int) -> list[PresenceSessionRow]:
    rows = await session.scalars(
        select(PresenceSessionRow)
        .where(
            PresenceSessionRow.node_id == node_id,
            PresenceSessionRow.record == PresenceRecord.ON_RECORD,
            PresenceSessionRow.status == PresenceStatus.CLOSED,
            visible(PresenceSessionRow.author_account_id, PresenceSessionRow.shared),
        )
        .order_by(PresenceSessionRow.id.desc())
    )
    return list(rows)


async def session_exchanges(session: AsyncSession, session_id: int) -> list[PresenceExchangeRow]:
    rows = await session.scalars(select(PresenceExchangeRow).where(PresenceExchangeRow.session_id == session_id).order_by(PresenceExchangeRow.ordinal))
    return list(rows)


async def exchange_counts(session: AsyncSession, session_ids: Sequence[int]) -> dict[int, int]:
    if not session_ids:
        return {}
    rows = await session.execute(
        select(PresenceExchangeRow.session_id, func.count())
        .where(PresenceExchangeRow.session_id.in_(session_ids))
        .group_by(PresenceExchangeRow.session_id)
        .order_by(PresenceExchangeRow.session_id)
    )
    return {session_id: int(count) for session_id, count in rows}


async def window_exchanges(session: AsyncSession, session_id: int, remembered: int, before_ordinal: int | None = None) -> list[PresenceExchangeRow]:
    statement = select(PresenceExchangeRow).where(PresenceExchangeRow.session_id == session_id, PresenceExchangeRow.status.in_(FINISHED_EXCHANGES))
    if before_ordinal is not None:
        statement = statement.where(PresenceExchangeRow.ordinal < before_ordinal)
    rows = list(await session.scalars(statement.order_by(PresenceExchangeRow.ordinal.desc()).limit(remembered)))
    return list(reversed(rows))


async def forgotten_before(session: AsyncSession, exchange: PresenceExchangeRow, kept: int) -> int:
    before = await session.scalar(
        select(func.count())
        .select_from(PresenceExchangeRow)
        .where(
            PresenceExchangeRow.session_id == exchange.session_id,
            PresenceExchangeRow.ordinal < exchange.ordinal,
            PresenceExchangeRow.status.in_(FINISHED_EXCHANGES),
        )
    )
    return max(0, int(before or 0) - kept)


async def memory_boundary(session: AsyncSession, session_id: int, remembered: int) -> int:
    window = await window_exchanges(session, session_id, remembered)
    return window[0].ordinal if window else FIRST_ORDINAL


async def running_exchange(session: AsyncSession, session_id: int) -> PresenceExchangeRow | None:
    return await session.scalar(
        select(PresenceExchangeRow)
        .where(PresenceExchangeRow.session_id == session_id, PresenceExchangeRow.status == PresenceExchangeStatus.RUNNING)
        .order_by(PresenceExchangeRow.ordinal)
        .limit(1)
    )


async def events_by_exchange(session: AsyncSession, exchange_ids: Sequence[int]) -> dict[int, list[PresenceEventRow]]:
    found: dict[int, list[PresenceEventRow]] = defaultdict(list)
    if not exchange_ids:
        return found
    rows = await session.scalars(
        select(PresenceEventRow).where(PresenceEventRow.exchange_id.in_(exchange_ids)).order_by(PresenceEventRow.exchange_id, PresenceEventRow.ordinal)
    )
    for row in rows:
        found[row.exchange_id].append(row)
    return found


async def next_exchange_ordinal(session: AsyncSession, session_id: int) -> int:
    found = await session.scalar(select(func.coalesce(func.max(PresenceExchangeRow.ordinal), 0) + 1).where(PresenceExchangeRow.session_id == session_id))
    return int(found or FIRST_ORDINAL)


async def next_event_ordinal(session: AsyncSession, exchange_id: int) -> int:
    found = await session.scalar(select(func.coalesce(func.max(PresenceEventRow.ordinal), 0) + 1).where(PresenceEventRow.exchange_id == exchange_id))
    return int(found or FIRST_ORDINAL)


async def add_event(
    session: AsyncSession, exchange_id: int, kind: PresenceEventKind, *, tool: str = "", payload: Mapping[str, Any] | None = None
) -> PresenceEventRow:
    row = PresenceEventRow(exchange_id=exchange_id, ordinal=await next_event_ordinal(session, exchange_id), kind=kind, tool=tool, payload=dict(payload or {}))
    session.add(row)
    await session.flush()
    return row
