import asyncio
import logging
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.activity import ActivityLog, collecting
from aerona.core.errors import BusyError, ConflictError
from aerona.core.grammar import several
from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.types import json_missing
from aerona.domain.enums.entity import LIVING_STATUSES, EntityStatus
from aerona.domain.enums.job import JobKind, JobStatus
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.jobs.context import JOB_LABEL_KEY, JobContext
from aerona.jobs.manager import JobManager
from aerona.rules.registry import Rules
from aerona.services.lore_ports import EntityDeepener, PendingNamer

logger = logging.getLogger(__name__)

Sleeper = Callable[[float], Awaitable[None]]
DISABLED = "Deepening needs the language model, which is turned off."
READ_ONLY = "Bulk deepening is paused while a guest world is open."


class TargetKind(StrEnum):
    ENTITY = "entity"
    FOREIGN_GOD = "foreign_god"


class LogLevel(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class QueueItem:
    kind: TargetKind
    id: int
    name: str


@dataclass(frozen=True)
class LogLine:
    level: LogLevel
    at: datetime
    text: str


@dataclass
class BulkState:
    running: bool = False
    stop_requested: bool = False
    total: int = 0
    done: int = 0
    failed: int = 0
    skipped: int = 0
    current: list[QueueItem] = field(default_factory=list)
    started: datetime | None = None
    finished: datetime | None = None

    @property
    def remaining(self) -> int:
        return max(0, self.total - self.done - self.failed - self.skipped)


@dataclass(frozen=True)
class BulkStatus:
    state: BulkState
    log: list[LogLine]
    waiting: int
    unnamed: int


async def deepening_queue(session: AsyncSession) -> list[QueueItem]:
    gods = [
        QueueItem(TargetKind.FOREIGN_GOD, god.id, god.name)
        for god in await session.scalars(select(ForeignGodRow).where(json_missing(ForeignGodRow.depth)).order_by(ForeignGodRow.id))
    ]
    statement = (
        select(EntityRow)
        .where(json_missing(EntityRow.depth), EntityRow.status.in_(list(LIVING_STATUSES)))
        .order_by(EntityRow.pending_name, func.coalesce(EntityRow.importance, 0).desc(), EntityRow.power_level.desc(), EntityRow.id)
    )
    return gods + [QueueItem(TargetKind.ENTITY, entity.id, entity.name) for entity in await session.scalars(statement)]


async def unnamed_count(session: AsyncSession) -> int:
    statement = select(func.count()).select_from(EntityRow).where(EntityRow.pending_name.is_(True), EntityRow.status == EntityStatus.CANON)
    return int(await session.scalar(statement) or 0)


class BulkDeepening:
    def __init__(
        self,
        database: Database,
        rules: Callable[[], Rules],
        deepener: EntityDeepener | None,
        *,
        namer: PendingNamer | None = None,
        bus: EventBus | None = None,
        read_only: Callable[[], bool] = lambda: False,
        sleep: Sleeper = asyncio.sleep,
        jobs: JobManager | None = None,
    ) -> None:
        self._database = database
        self._rules = rules
        self._deepener = deepener
        self._namer = namer
        self._bus = bus
        self._read_only = read_only
        self._sleep = sleep
        self._jobs = jobs
        self._tracked: tuple[JobContext, ActivityLog] | None = None
        self.state = BulkState()
        self._log: deque[LogLine] = deque(maxlen=rules().batch.log_lines)
        self._task: asyncio.Task[None] | None = None

    def log(self, level: LogLevel, text: str) -> None:
        if self._log.maxlen != self._rules().batch.log_lines:
            self._log = deque(self._log, maxlen=self._rules().batch.log_lines)
        self._log.append(LogLine(level, datetime.now(UTC), text))
        if self._bus is not None:
            self._bus.publish(EventKind.BATCH_DEEPEN_LOG, {"level": level.value, "line": text, **self._summary()})

    def _summary(self) -> dict[str, Any]:
        state = self.state
        return {
            "running": state.running,
            "total": state.total,
            "done": state.done,
            "failed": state.failed,
            "skipped": state.skipped,
            "remaining": state.remaining,
        }

    async def status(self) -> BulkStatus:
        async with self._database.read() as session:
            return BulkStatus(self.state, list(self._log), len(await deepening_queue(session)), await unnamed_count(session))

    async def deepen_one(self, kind: TargetKind, target_id: int) -> None:
        deepener = self._require()
        if kind is TargetKind.FOREIGN_GOD:
            await deepener.deepen_foreign_god(target_id)
            event = EventKind.FOREIGN_GOD_DEEPENED
        else:
            await deepener.deepen_entity(target_id)
            event = EventKind.ENTITY_DEEPENED
        if self._bus is not None:
            self._bus.publish(event, {"id": target_id})

    def _require(self) -> EntityDeepener:
        if self._deepener is None:
            raise ConflictError(DISABLED)
        return self._deepener

    async def start(self) -> BulkState:
        self._require()
        if self._read_only():
            raise ConflictError(READ_ONLY)
        if self.state.running:
            raise ConflictError("Bulk deepening is already running.")
        async with self._database.read() as session:
            queue = await deepening_queue(session)
        if not queue:
            raise ConflictError("No undeepened records left.")
        self.state = BulkState(running=True, total=len(queue), started=datetime.now(UTC))
        self.log(LogLevel.INFO, f"Bulk deepening started: {several(len(queue), 'record', 'records')}, by importance.")
        if self._jobs is not None:
            self._tracked = await self._jobs.begin_external(
                JobKind.DEEPEN, {JOB_LABEL_KEY: f"bulk deepening of {several(len(queue), 'record', 'records')}", "total": len(queue)}
            )
        self._task = asyncio.create_task(self._run(queue))
        return self.state

    def stop(self) -> BulkState:
        if not self.state.running:
            raise ConflictError("No bulk deepening is running.")
        self.state.stop_requested = True
        self.log(LogLevel.INFO, "Stop requested; it will stop once the records in progress finish.")
        return self.state

    async def wait(self) -> None:
        if self._task is not None:
            await self._task

    def _report(self, name: str) -> None:
        if self._tracked is None or self._jobs is None:
            return
        context = self._tracked[0]
        handled = self.state.done + self.state.failed + self.state.skipped
        context.progress = handled / max(1, self.state.total)
        context.stage = f"{handled} of {self.state.total} · {name}"
        self._jobs.report_external(context)

    async def _run(self, queue: list[QueueItem]) -> None:
        log = self._tracked[1] if self._tracked is not None else ActivityLog()
        failure: str | None = None
        with collecting(log):
            try:
                await self._run_queue(queue)
            except Exception as error:
                failure = str(error)
        if self._tracked is not None and self._jobs is not None:
            state = self.state
            status = JobStatus.FAILED if failure else JobStatus.CANCELLED if state.stop_requested else JobStatus.SUCCEEDED
            summary = {"total": state.total, "done": state.done, "failed": state.failed, "skipped": state.skipped}
            await self._jobs.end_external(self._tracked[0], self._tracked[1], status, summary, failure)
            self._tracked = None

    async def _run_queue(self, queue: list[QueueItem]) -> None:
        try:
            naming: asyncio.Task[int] | None = None
            async with self._database.read() as session:
                unnamed = await unnamed_count(session)
            if unnamed and self._namer is not None:
                self.log(LogLevel.INFO, f"{several(unnamed, 'unnamed record is', 'unnamed records are')} also being named.")
                naming = asyncio.create_task(self._namer.name_pending())
            seen = {(item.kind, item.id) for item in queue}
            await self._round(deque(queue))
            if naming is not None and not self.state.stop_requested:
                await naming
                async with self._database.read() as session:
                    extra = [item for item in await deepening_queue(session) if (item.kind, item.id) not in seen]
                if extra:
                    self.state.total += len(extra)
                    await self._round(deque(extra))
            elif naming is not None:
                naming.cancel()
            verb = "Stopped" if self.state.stop_requested else "Done"
            self.log(LogLevel.INFO, f"{verb}: {self.state.done} deepened, {several(self.state.failed, 'error', 'errors')}, {self.state.skipped} skipped.")
        except Exception as error:
            logger.exception("bulk deepening crashed")
            self.log(LogLevel.ERROR, f"The bulk job stopped unexpectedly: {error}")
        finally:
            self.state.running = False
            self.state.finished = datetime.now(UTC)

    async def _round(self, queue: deque[QueueItem]) -> None:
        workers = max(1, self._rules().batch.concurrent)
        await asyncio.gather(*(self._worker(queue) for _ in range(workers)))

    async def _worker(self, queue: deque[QueueItem]) -> None:
        first = True
        while queue and not self.state.stop_requested:
            if not first:
                await self._sleep(self._rules().batch.wait_seconds)
            first = False
            await self._one(queue.popleft())

    async def _still_needed(self, item: QueueItem) -> bool:
        async with self._database.read() as session:
            if item.kind is TargetKind.FOREIGN_GOD:
                god = await session.get(ForeignGodRow, item.id)
                return god is not None and god.depth is None
            entity = await session.get(EntityRow, item.id)
            return entity is not None and entity.depth is None and entity.status in LIVING_STATUSES

    async def _one(self, item: QueueItem) -> None:
        if not await self._still_needed(item):
            self.state.skipped += 1
            return
        self.state.current.append(item)
        self.log(LogLevel.INFO, f"Deepening: {item.name}")
        self._report(item.name)
        rules = self._rules().batch
        attempts = 0
        started = time.monotonic()
        try:
            while True:
                try:
                    await self.deepen_one(item.kind, item.id)
                except BusyError:
                    if self.state.stop_requested:
                        self.state.skipped += 1
                        self.log(LogLevel.WARNING, f"{item.name}: stopped while waiting in the queue; not processed.")
                        return
                    await self._sleep(rules.pool_wait_seconds)
                    continue
                except Exception as error:
                    attempts += 1
                    if attempts > rules.retries or self.state.stop_requested:
                        self.state.failed += 1
                        self.log(LogLevel.ERROR, f"{item.name} could not be deepened: {error}")
                        return
                    self.log(LogLevel.WARNING, f"{item.name}: {error}; retrying ({attempts}/{rules.retries}).")
                    await self._sleep(rules.retry_wait_seconds)
                    continue
                self.state.done += 1
                self.log(LogLevel.INFO, f"{item.name} deepened ({round(time.monotonic() - started)} s)")
                return
        finally:
            self.state.current.remove(item)

    async def shutdown(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
