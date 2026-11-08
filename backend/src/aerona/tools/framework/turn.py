from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.agency import AgentTurnRow, TurnCounterRow
from aerona.domain.enums.agent import AgentKind, TurnCounter
from aerona.domain.models.turn import LongJobTrace, PendingJob, TurnContext


class TurnState:
    def __init__(self, row: AgentTurnRow) -> None:
        self.row = row

    @property
    def epoch(self) -> int:
        return self.row.epoch

    @property
    def action_points(self) -> int:
        return self.row.action_points_left or 0

    @property
    def context(self) -> TurnContext:
        return self.row.context

    def spend(self, amount: int) -> None:
        self.row.action_points_left = max(0, self.action_points - max(0, amount))

    def refund(self, amount: int) -> None:
        self.row.action_points_left = self.action_points + max(0, amount)

    def exhaust(self) -> None:
        self.row.action_points_left = 0

    def remember_creation(self, entity_id: int) -> None:
        self.row.context = self.context.with_creation(entity_id)

    def remember_harvest(self, resource_id: int) -> None:
        self.row.context = self.context.model_copy(update={"harvested_resource_ids": (*self.context.harvested_resource_ids, resource_id)})

    def note_level_up(self, note: str | None) -> None:
        self.row.context = self.context.model_copy(update={"level_up_note": note})

    def set_pending_job(self, job: PendingJob | None) -> None:
        self.row.context = self.context.with_pending_job(job)

    def add_long_job_trace(self, trace: LongJobTrace) -> None:
        self.row.context = self.context.model_copy(update={"long_jobs": (*self.context.long_jobs, trace)})


@dataclass(frozen=True)
class TurnStart:
    action_points: int
    resumed: bool


async def _open_turn(session: AsyncSession, node_id: int, kind: AgentKind, epoch: int, action_points: int) -> AgentTurnRow:
    row = await session.get(AgentTurnRow, node_id)
    if row is None:
        row = AgentTurnRow(agent_node_id=node_id, agent_kind=kind, epoch=epoch, action_points_left=action_points, context=TurnContext(), finished=False)
        session.add(row)
    else:
        row.agent_kind = kind
        row.epoch = epoch
        row.action_points_left = action_points
        row.context = TurnContext()
        row.finished = False
    await session.flush()
    return row


async def start_turn(session: AsyncSession, node_id: int, kind: AgentKind, epoch: int, action_points: int) -> TurnStart:
    row = await session.get(AgentTurnRow, node_id)
    if row is not None and row.epoch == epoch and not row.finished and row.action_points_left is not None:
        return TurnStart(row.action_points_left, True)
    await _open_turn(session, node_id, kind, epoch, action_points)
    return TurnStart(action_points, False)


async def load_turn(session: AsyncSession, node_id: int, kind: AgentKind, epoch: int) -> TurnState:
    row = await session.get(AgentTurnRow, node_id)
    if row is None or row.epoch != epoch:
        row = await _open_turn(session, node_id, kind, epoch, 0)
    return TurnState(row)


async def peek_turn(session: AsyncSession, node_id: int, kind: AgentKind, epoch: int) -> TurnState:
    row = await session.get(AgentTurnRow, node_id)
    if row is None or row.epoch != epoch:
        row = AgentTurnRow(agent_node_id=node_id, agent_kind=kind, epoch=epoch, action_points_left=0, context=TurnContext(), finished=False)
    return TurnState(row)


async def counter_value(session: AsyncSession, node_id: int, epoch: int, counter: TurnCounter) -> int:
    row = await session.get(TurnCounterRow, (node_id, epoch, counter))
    return row.value if row is not None else 0


async def bump_counter(session: AsyncSession, node_id: int, epoch: int, counter: TurnCounter, amount: int = 1) -> int:
    row = await session.get(TurnCounterRow, (node_id, epoch, counter))
    if row is None:
        row = TurnCounterRow(agent_node_id=node_id, epoch=epoch, counter=counter, value=0)
        session.add(row)
    row.value = max(0, row.value + amount)
    await session.flush()
    return row.value
