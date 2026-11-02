from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.agency import AgentTurnRow, TurnCounterRow
from aerona.domain.enums.agent import AgentKind, TurnCounter
from aerona.domain.models.turn import TurnContext
from aerona.prompts.contexts.son_turn import LongJobNote


@dataclass(frozen=True)
class TurnStart:
    resumed: bool
    action_points: int
    context: TurnContext


def is_resumable(row: AgentTurnRow | None, epoch: int) -> bool:
    return row is not None and row.epoch == epoch and row.action_points_left is not None and not row.finished


async def turn_row(session: AsyncSession, node_id: int) -> AgentTurnRow | None:
    return await session.get(AgentTurnRow, node_id)


async def long_job_notes(session: AsyncSession, node_id: int, summary_chars: int) -> list[LongJobNote]:
    row = await turn_row(session, node_id)
    if row is None:
        return []
    return [LongJobNote(tool=trace.tool, summary=trace.summary[:summary_chars]) for trace in row.context.long_jobs]


async def epoch_counters(session: AsyncSession, node_id: int, epoch: int) -> dict[TurnCounter, int]:
    rows = await session.scalars(select(TurnCounterRow).where(TurnCounterRow.agent_node_id == node_id, TurnCounterRow.epoch == epoch))
    return {row.counter: row.value for row in rows}


async def begin_turn(session: AsyncSession, node_id: int, kind: AgentKind, epoch: int, fresh_points: int) -> TurnStart:
    row = await turn_row(session, node_id)
    counters = await epoch_counters(session, node_id, epoch)
    if row is not None and is_resumable(row, epoch) and row.action_points_left is not None:
        context = row.context.model_copy(update={"counters": {**counters, **row.context.counters}})
        row.context = context
        return TurnStart(True, row.action_points_left, context)
    context = TurnContext(counters=counters)
    if row is None:
        session.add(AgentTurnRow(agent_node_id=node_id, agent_kind=kind, epoch=epoch, action_points_left=fresh_points, context=context, finished=False))
    else:
        row.agent_kind = kind
        row.epoch = epoch
        row.action_points_left = fresh_points
        row.context = context
        row.finished = False
    await session.flush()
    return TurnStart(False, fresh_points, context)


async def save_turn(session: AsyncSession, node_id: int, action_points: int, context: TurnContext) -> None:
    row = await turn_row(session, node_id)
    if row is None:
        return
    row.action_points_left = action_points
    row.context = context


async def finish_turn(session: AsyncSession, node_id: int) -> None:
    row = await turn_row(session, node_id)
    if row is not None:
        row.action_points_left = None
        row.finished = True
