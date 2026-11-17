import asyncio
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.chronicle import ChroniclePhase, record_line
from aerona.agents.turns.state import is_resumable
from aerona.db.tables.agency import AgentTurnRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.agent import AgentKind, PendingJobKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.models.turn import PendingJob
from aerona.rules.registry import Rules

JOB_NOUNS = {PendingJobKind.WORLD_BIRTH: "world birth", PendingJobKind.CHILD_BIRTH: "child birth"}


class LongJobResult(StrEnum):
    RUNNING = "running"
    DONE = "done"
    REFUNDED = "refunded"


@dataclass(frozen=True)
class ResolvedJob:
    son_id: int
    son_name: str
    result: LongJobResult


class LongJobRegistry:
    def __init__(self) -> None:
        self._running: dict[int, asyncio.Task[object]] = {}

    def register(self, agent_node_id: int, task: asyncio.Task[object]) -> None:
        self._running[agent_node_id] = task
        task.add_done_callback(lambda _: self._running.pop(agent_node_id, None))

    def running(self, agent_node_id: int) -> asyncio.Task[object] | None:
        task = self._running.get(agent_node_id)
        return task if task is not None and not task.done() else None

    async def wait(self, agent_node_id: int) -> None:
        task = self.running(agent_node_id)
        if task is not None:
            await asyncio.gather(task, return_exceptions=True)


LONG_JOBS = LongJobRegistry()


async def job_completed(session: AsyncSession, son_id: int, job: PendingJob) -> bool:
    if job.kind is PendingJobKind.WORLD_BIRTH:
        found = await session.scalar(select(WorldRow.id).where(WorldRow.creator_son_id == son_id, WorldRow.created_epoch == job.epoch).limit(1))
    else:
        found = await session.scalar(select(SonRow.id).where(SonRow.parent_son_id == son_id, SonRow.birth_epoch == job.epoch).limit(1))
    return found is not None


async def resolve_pending_job(session: AsyncSession, rules: Rules, son: SonRow, row: AgentTurnRow, epoch: int) -> LongJobResult | None:
    job = row.context.pending_job
    if job is None:
        return None
    if LONG_JOBS.running(son.id) is not None:
        return LongJobResult.RUNNING
    row.context = row.context.with_pending_job(None)
    if await job_completed(session, son.id, job):
        return LongJobResult.DONE
    son.essence += job.essence
    if is_resumable(row, epoch) and son.last_acted_epoch < epoch and row.action_points_left is not None:
        row.action_points_left += job.action_points
    await record_line(
        session,
        rules,
        "agents.long_job_refund",
        roles={IncidentRole.SUBJECT: son.id},
        facts={"work": JOB_NOUNS[job.kind], "essence": job.essence},
        phase=ChroniclePhase.GODS,
        kind=ChronicleKind.SYSTEM,
        son_id=son.id,
    )
    return LongJobResult.REFUNDED


async def resolve_orphaned_jobs(session: AsyncSession, rules: Rules, epoch: int) -> list[ResolvedJob]:
    rows = await session.scalars(select(AgentTurnRow).where(AgentTurnRow.agent_kind == AgentKind.SON))
    resolved: list[ResolvedJob] = []
    for row in rows:
        if row.context.pending_job is None or LONG_JOBS.running(row.agent_node_id) is not None:
            continue
        son = await session.get(SonRow, row.agent_node_id)
        if son is None:
            continue
        result = await resolve_pending_job(session, rules, son, row, epoch)
        if result is not None:
            resolved.append(ResolvedJob(son.id, son.name, result))
    await session.flush()
    return resolved
