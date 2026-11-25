import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import CursorResult, select, update

from aerona.constants.timeouts import JOB_SHUTDOWN_GRACE_SECONDS
from aerona.core.account_scope import detached
from aerona.core.activity import ActivityLog, collecting
from aerona.core.errors import BusyError, NotFoundError
from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.job import JobRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.job import JobKind, JobStatus
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.jobs.context import JOB_LABEL_KEY, JobContext

JobHandler = Callable[[JobContext], Awaitable[dict[str, Any] | None]]
Capacity = Callable[[], int]

logger = logging.getLogger(__name__)
ReleaseHook = Callable[[str], Awaitable[None]]
RUNNING_GROUP: ContextVar[str | None] = ContextVar("running_group", default=None)


def running_group() -> str | None:
    return RUNNING_GROUP.get()


UNTRACKED_KINDS = frozenset({JobKind.EPOCH, JobKind.SIMULATION, JobKind.BACKUP, JobKind.IMPORT})
ITEMS_KEY = "items"


class JobManager:
    def __init__(self, database: Database, bus: EventBus, capacity: Capacity | None = None) -> None:
        self._database = database
        self._bus = bus
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._contexts: dict[str, JobContext] = {}
        self._groups: dict[str, str] = {}
        self._keys: dict[str, str] = {}
        self._capacity = capacity
        self._running = 0
        self._slot_freed = asyncio.Condition()
        self._release_hooks: list[ReleaseHook] = []
        self._release_tasks: set[asyncio.Task[None]] = set()
        self._closing = False

    def bind_capacity(self, capacity: Capacity) -> None:
        self._capacity = capacity

    def on_group_released(self, hook: ReleaseHook) -> None:
        self._release_hooks.append(hook)

    def _released(self, group: str) -> None:
        if self._closing:
            return
        for hook in self._release_hooks:
            task = detached(self._run_hook(hook, group))
            self._release_tasks.add(task)
            task.add_done_callback(self._release_tasks.discard)

    async def _run_hook(self, hook: ReleaseHook, group: str) -> None:
        try:
            await hook(group)
        except Exception:
            logger.exception("release hook for %s failed", group)

    @property
    def queued_count(self) -> int:
        return len(self._tasks) - self._running

    async def _acquire(self) -> None:
        async with self._slot_freed:
            await self._slot_freed.wait_for(lambda: self._capacity is None or self._running < max(1, self._capacity()))
            self._running += 1

    async def _release(self) -> None:
        async with self._slot_freed:
            self._running -= 1
            self._slot_freed.notify_all()

    async def recover_interrupted(self) -> int:
        async with self._database.write() as session:
            statement = (
                update(JobRow)
                .where(JobRow.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]))
                .values(status=JobStatus.INTERRUPTED, finished_at=datetime.now(UTC))
            )
            result = cast(CursorResult[tuple[()]], await session.execute(statement))
        return int(result.rowcount or 0)

    @property
    def running_count(self) -> int:
        return len(self._tasks)

    def busy_group(self, group: str) -> str | None:
        return self._groups.get(group)

    def active_groups(self) -> list[str]:
        return sorted(self._groups)

    def running_context(self, job_id: str) -> JobContext | None:
        return self._contexts.get(job_id)

    def kind_running(self, kind: JobKind) -> bool:
        return any(context.kind is kind for context in self._contexts.values())

    async def submit(
        self,
        kind: JobKind,
        handler: JobHandler,
        params: dict[str, Any] | None = None,
        exclusive_group: str | None = None,
        dedupe_key: str | None = None,
        *,
        as_person: bool = False,
    ) -> str:
        if exclusive_group and exclusive_group in self._groups:
            raise BusyError(f"Another {exclusive_group} job is already running.")
        if dedupe_key is not None and dedupe_key in self._keys:
            return self._keys[dedupe_key]
        job_id = str(uuid.uuid4())
        job_params = params or {}
        async with self._database.write() as session:
            session.add(JobRow(id=job_id, kind=kind, status=JobStatus.QUEUED, exclusive_group=exclusive_group, params=job_params))
        if exclusive_group:
            self._groups[exclusive_group] = job_id
        if dedupe_key is not None:
            self._keys[dedupe_key] = job_id
        context = JobContext(job_id=job_id, kind=kind, params=job_params, bus=self._bus)
        self._contexts[job_id] = context
        self._bus.publish(EventKind.JOB_QUEUED, {"job_id": job_id, "kind": kind.value})
        run = self._run(context, handler, exclusive_group, dedupe_key)
        self._tasks[job_id] = asyncio.create_task(run) if as_person else detached(run)
        return job_id

    async def cancel(self, job_id: str) -> None:
        task = self._tasks.get(job_id)
        if task is None:
            raise NotFoundError("Job is not running.")
        task.cancel()

    async def shutdown(self) -> None:
        self._closing = True
        for task in [*self._tasks.values(), *self._release_tasks]:
            task.cancel()
        if self._tasks:
            await asyncio.wait(list(self._tasks.values()), timeout=JOB_SHUTDOWN_GRACE_SECONDS)

    def _live(self, row: JobRow) -> JobRow:
        context = self._contexts.get(row.id)
        if context is not None and row.status is JobStatus.RUNNING:
            row.progress = context.progress
            row.stage = context.stage
        return row

    async def get(self, job_id: str) -> JobRow:
        async with self._database.read() as session:
            row = await session.get(JobRow, job_id)
        if row is None:
            raise NotFoundError("Job not found.")
        return self._live(row)

    async def list_recent(self, limit: int) -> list[JobRow]:
        async with self._database.read() as session:
            rows = await session.scalars(select(JobRow).order_by(JobRow.created_at.desc()).limit(limit))
            return [self._live(row) for row in rows]

    async def _items(self, log: ActivityLog) -> list[dict[str, Any]]:
        if not log.items:
            return []
        ids = {item.node_id for item in log.items.values()} | {item.other_id for item in log.items.values() if item.other_id is not None}
        async with self._database.read() as session:
            nodes = {
                node_id: (kind, name)
                for node_id, kind, name in await session.execute(select(NodeRow.id, NodeRow.kind, NodeRow.name).where(NodeRow.id.in_(ids)))
            }
            typed = await session.execute(select(EntityRow.id, EntityRow.entity_type).where(EntityRow.id.in_(ids)))
            types = {entity_id: entity_type for entity_id, entity_type in typed}
        found: list[dict[str, Any]] = []
        for item in log.items.values():
            node = nodes.get(item.node_id)
            if node is None:
                continue
            other = nodes.get(item.other_id) if item.other_id is not None else None
            found.append(
                {
                    "node_id": item.node_id,
                    "node_kind": node[0].value,
                    "name": node[1],
                    "entity_type": types[item.node_id].value if item.node_id in types else None,
                    "action": item.action,
                    "note": item.note,
                    "other_id": item.other_id if other is not None else None,
                    "other_kind": other[0].value if other is not None else None,
                    "other_name": other[1] if other is not None else None,
                }
            )
        return found

    async def _with_items(self, log: ActivityLog, result: dict[str, Any] | None) -> dict[str, Any] | None:
        items = await self._items(log)
        if not items:
            return result
        return {**(result or {}), ITEMS_KEY: items}

    async def begin_external(self, kind: JobKind, params: dict[str, Any] | None = None) -> tuple[JobContext, ActivityLog]:
        job_id = str(uuid.uuid4())
        job_params = params or {}
        now = datetime.now(UTC)
        async with self._database.write() as session:
            session.add(JobRow(id=job_id, kind=kind, status=JobStatus.RUNNING, params=job_params, started_at=now))
        context = JobContext(job_id=job_id, kind=kind, params=job_params, bus=self._bus)
        self._contexts[job_id] = context
        self._bus.publish(EventKind.JOB_STARTED, {"job_id": job_id, "kind": kind.value})
        return context, ActivityLog()

    def report_external(self, context: JobContext) -> None:
        self._bus.publish(EventKind.JOB_PROGRESS, {"job_id": context.job_id, "kind": context.kind.value, "progress": context.progress, "stage": context.stage})

    async def end_external(
        self, context: JobContext, log: ActivityLog, status: JobStatus, result: dict[str, Any] | None = None, error: str | None = None
    ) -> None:
        stored = await self._with_items(log, result)
        progress = 1.0 if status is JobStatus.SUCCEEDED else context.progress
        await self._set(context.job_id, status=status, progress=progress, stage=context.stage, result=stored, error=error, finished_at=datetime.now(UTC))
        self._contexts.pop(context.job_id, None)
        base = {"job_id": context.job_id, "kind": context.kind.value, "label": context.params.get(JOB_LABEL_KEY)}
        if status is JobStatus.SUCCEEDED:
            self._bus.publish(EventKind.JOB_FINISHED, {**base, "result": stored})
        elif status is JobStatus.CANCELLED:
            self._bus.publish(EventKind.JOB_CANCELLED, base)
        else:
            self._bus.publish(EventKind.JOB_FAILED, {**base, "error": error or ""})

    async def _set(self, job_id: str, **values: Any) -> None:
        async with self._database.write() as session:
            await session.execute(update(JobRow).where(JobRow.id == job_id).values(**values))

    async def _run(self, context: JobContext, handler: JobHandler, exclusive_group: str | None, dedupe_key: str | None = None) -> None:
        job_id = context.job_id
        base = {"job_id": job_id, "kind": context.kind.value, "label": context.params.get(JOB_LABEL_KEY)}
        acquired = False
        log = ActivityLog()
        try:
            await self._acquire()
            acquired = True
            await self._set(job_id, status=JobStatus.RUNNING, started_at=datetime.now(UTC))
            self._bus.publish(EventKind.JOB_STARTED, base)
            group_token = RUNNING_GROUP.set(exclusive_group)
            try:
                if context.kind in UNTRACKED_KINDS:
                    result = await handler(context)
                else:
                    with collecting(log):
                        result = await handler(context)
            finally:
                RUNNING_GROUP.reset(group_token)
            stored = await self._with_items(log, result)
            finished = datetime.now(UTC)
            await self._set(job_id, status=JobStatus.SUCCEEDED, progress=1.0, result=stored, stage=context.stage, finished_at=finished)
            self._bus.publish(EventKind.JOB_FINISHED, {**base, "result": stored})
        except asyncio.CancelledError:
            partial = await self._with_items(log, None)
            await self._set(job_id, status=JobStatus.CANCELLED, progress=context.progress, stage=context.stage, result=partial, finished_at=datetime.now(UTC))
            self._bus.publish(EventKind.JOB_CANCELLED, base)
        except Exception as error:
            logger.exception("job %s failed", job_id)
            failed = datetime.now(UTC)
            partial = await self._with_items(log, None)
            await self._set(
                job_id, status=JobStatus.FAILED, error=str(error), progress=context.progress, stage=context.stage, result=partial, finished_at=failed
            )
            self._bus.publish(EventKind.JOB_FAILED, {**base, "error": str(error)})
        finally:
            if acquired:
                await self._release()
            self._tasks.pop(job_id, None)
            self._contexts.pop(job_id, None)
            if exclusive_group and self._groups.get(exclusive_group) == job_id:
                self._groups.pop(exclusive_group, None)
                self._released(exclusive_group)
            if dedupe_key is not None and self._keys.get(dedupe_key) == job_id:
                self._keys.pop(dedupe_key, None)
