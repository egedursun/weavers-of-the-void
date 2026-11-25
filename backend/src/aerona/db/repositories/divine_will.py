from collections.abc import Mapping
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.authorship import mine
from aerona.db.tables.divine_will import DivineWillCycleRow, DivineWillEventRow, DivineWillSessionRow
from aerona.domain.enums.divine_will import CycleEventKind, CycleStatus

FIRST_ORDINAL = 1
FINISHED_CYCLES = frozenset({CycleStatus.DONE, CycleStatus.FAILED, CycleStatus.CANCELLED})


async def active_session(session: AsyncSession) -> DivineWillSessionRow | None:
    statement = select(DivineWillSessionRow).where(DivineWillSessionRow.closed_at.is_(None), mine(DivineWillSessionRow.author_account_id))
    return await session.scalar(statement.order_by(DivineWillSessionRow.id.desc()).limit(1))


async def window_cycles(session: AsyncSession, session_id: int, remembered: int, before_ordinal: int | None = None) -> list[DivineWillCycleRow]:
    statement = select(DivineWillCycleRow).where(DivineWillCycleRow.session_id == session_id, DivineWillCycleRow.status.in_(FINISHED_CYCLES))
    if before_ordinal is not None:
        statement = statement.where(DivineWillCycleRow.ordinal < before_ordinal)
    rows = list(await session.scalars(statement.order_by(DivineWillCycleRow.ordinal.desc()).limit(remembered)))
    return list(reversed(rows))


async def memory_boundary(session: AsyncSession, session_id: int, remembered: int) -> int:
    window = await window_cycles(session, session_id, remembered)
    return window[0].ordinal if window else FIRST_ORDINAL


async def remembered_cycle_ids(session: AsyncSession, session_id: int, remembered: int) -> set[int]:
    window = {row.id for row in await window_cycles(session, session_id, remembered)}
    open_rows = await session.scalars(
        select(DivineWillCycleRow.id).where(DivineWillCycleRow.session_id == session_id, DivineWillCycleRow.status.not_in(FINISHED_CYCLES))
    )
    return window | set(open_rows)


async def cycle_events(session: AsyncSession, cycle_id: int) -> list[DivineWillEventRow]:
    rows = await session.scalars(select(DivineWillEventRow).where(DivineWillEventRow.cycle_id == cycle_id).order_by(DivineWillEventRow.ordinal))
    return list(rows)


async def next_event_ordinal(session: AsyncSession, cycle_id: int) -> int:
    return int(await session.scalar(select(func.coalesce(func.max(DivineWillEventRow.ordinal), 0) + 1).where(DivineWillEventRow.cycle_id == cycle_id)) or 1)


async def next_cycle_ordinal(session: AsyncSession, session_id: int) -> int:
    return int(await session.scalar(select(func.coalesce(func.max(DivineWillCycleRow.ordinal), 0) + 1).where(DivineWillCycleRow.session_id == session_id)) or 1)


async def add_event(
    session: AsyncSession, cycle_id: int, kind: CycleEventKind, *, tool: str = "", payload: Mapping[str, Any] | None = None, handle: str = ""
) -> DivineWillEventRow:
    row = DivineWillEventRow(
        cycle_id=cycle_id, ordinal=await next_event_ordinal(session, cycle_id), kind=kind, tool=tool, payload=dict(payload or {}), handle=handle
    )
    session.add(row)
    await session.flush()
    return row
