import asyncio
import json
import logging
import sqlite3
import time
from collections import deque
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.app import APP_VERSION
from aerona.core.universe_scope import current_universe
from aerona.db.telemetry.setup import TelemetryDatabase
from aerona.db.telemetry.tables import LiveEventRow, LlmCallRow
from aerona.domain.enums.meta import HealthStatus
from aerona.domain.enums.telemetry import LlmCallStatus
from aerona.events.bus import Event
from aerona.events.kinds import EventKind
from aerona.llm.records import CallRecord
from aerona.rules.registry import Rules

RECENT_ERRORS = 30
ERROR_TEXT_LIMIT = 2000
PRUNE_EVERY_WRITES = 50
SLOWEST_SHOWN = 12
LATEST_ERRORS_SHOWN = 8
ETA_EVENTS = 400
MILLISECONDS = 1000
SON_TURN_PREFIX = "Son turn:"
MORTAL_TURN_PREFIX = "Mortal turn:"
SON_TURN_GROUP = "Son turns"
MORTAL_TURN_GROUP = "Mortal turns"
QUICK_CHECK_OK = "ok"
WAL_SUFFIX = "-wal"
EVENT_KIND_VALUES = frozenset(kind.value for kind in EventKind)


@dataclass(frozen=True)
class LogEntry:
    level: str
    at: datetime
    text: str


class ErrorRing(logging.Handler):
    def __init__(self, size: int = RECENT_ERRORS) -> None:
        super().__init__(level=logging.WARNING)
        self._entries: deque[LogEntry] = deque(maxlen=size)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            text = record.getMessage()
            if record.exc_info:
                text = f"{text}\n{logging.Formatter().formatException(record.exc_info)}"
            self._entries.append(LogEntry(level=record.levelname, at=datetime.fromtimestamp(record.created, UTC), text=text[:ERROR_TEXT_LIMIT]))
        except Exception:
            self.handleError(record)

    def recent(self, limit: int) -> list[LogEntry]:
        return list(reversed(self._entries))[:limit]

    def errors_since(self, moment: datetime) -> list[LogEntry]:
        return [entry for entry in self._entries if entry.level in {"ERROR", "CRITICAL"} and entry.at >= moment]


class ErrorRouter(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.rings: dict[str | None, ErrorRing] = {}

    def emit(self, record: logging.LogRecord) -> None:
        ring = self.rings.get(current_universe())
        if ring is not None:
            ring.handle(record)


ERROR_ROUTER = ErrorRouter()


def install_error_ring(ring: ErrorRing, universe_id: str | None) -> None:
    ERROR_ROUTER.rings[universe_id] = ring
    root = logging.getLogger()
    if ERROR_ROUTER not in root.handlers:
        root.addHandler(ERROR_ROUTER)


def release_error_ring(ring: ErrorRing, universe_id: str | None) -> None:
    if ERROR_ROUTER.rings.get(universe_id) is ring:
        del ERROR_ROUTER.rings[universe_id]


def capture_loop_errors(loop: asyncio.AbstractEventLoop) -> None:
    logger = logging.getLogger("aerona.loop")

    def handle(_loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
        error = context.get("exception")
        logger.error("unhandled background error: %s", context.get("message"), exc_info=error if isinstance(error, BaseException) else None)

    loop.set_exception_handler(handle)


@dataclass(frozen=True)
class Totals:
    calls: int
    milliseconds: int
    cost: float
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class EpochMetrics:
    epoch: int
    calls: int
    milliseconds: int
    input_tokens: int
    output_tokens: int
    cost: float
    errors: int
    retried: int
    slow: int


@dataclass(frozen=True)
class ModelMetrics:
    model: str
    calls: int
    milliseconds: int
    average_ms: int
    input_tokens: int
    output_tokens: int
    cost: float


@dataclass(frozen=True)
class StepMetrics:
    step: str
    calls: int
    average_ms: int
    longest_ms: int
    cost: float
    errors: int


@dataclass(frozen=True)
class MetricsSummary:
    totals: Totals
    epochs: list[EpochMetrics]
    models: list[ModelMetrics]
    steps: list[StepMetrics]
    slowest: list[LlmCallRow]
    latest_errors: list[LlmCallRow]
    slow_threshold_ms: int


@dataclass(frozen=True)
class EpochEstimate:
    samples: int
    average_epoch_seconds: int | None
    average_phase_starts: dict[int, int]
    running: bool
    elapsed_seconds: int | None
    remaining_seconds: int | None
    phase: int | None
    overrun: bool


@dataclass(frozen=True)
class DatabaseHealth:
    file: str
    size: int
    wal_size: int
    quick_check: str


@dataclass(frozen=True)
class HealthReport:
    status: HealthStatus
    version: str
    uptime_seconds: int
    database: DatabaseHealth
    latest_backup: str | None
    latest_backup_age_minutes: int | None
    backup_count: int
    running_jobs: int
    read_only: bool
    log_file: str
    recent_errors: list[LogEntry] = field(default_factory=list)


def step_group(job: str) -> str:
    if job.startswith(SON_TURN_PREFIX):
        return SON_TURN_GROUP
    if job.startswith(MORTAL_TURN_PREFIX):
        return MORTAL_TURN_GROUP
    return job


def quick_check(path: Path) -> str:
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error as error:
        return str(error)
    try:
        row = connection.execute("PRAGMA quick_check").fetchone()
        return str(row[0]) if row else "unknown"
    except sqlite3.Error as error:
        return str(error)
    finally:
        connection.close()


class MetricsService:
    def __init__(self, telemetry: TelemetryDatabase, rules: Callable[[], Rules]) -> None:
        self._telemetry = telemetry
        self._rules = rules
        self._writes = 0
        self._started = time.monotonic()

    def sink(self, inner: Callable[[CallRecord], Awaitable[None]]) -> Callable[[CallRecord], Awaitable[None]]:
        async def counted(record: CallRecord) -> None:
            await inner(record)
            self._writes += 1
            if self._writes % PRUNE_EVERY_WRITES == 0:
                await self.prune()

        return counted

    async def prune(self) -> int:
        keep = self._rules().metrics.keep_epochs
        async with self._telemetry.sessions() as session, session.begin():
            top = await session.scalar(select(func.max(LlmCallRow.epoch)))
            if top is None:
                return 0
            result = await session.execute(delete(LlmCallRow).where(LlmCallRow.epoch <= int(top) - keep))
            return int(getattr(result, "rowcount", 0) or 0)

    async def record_events(self, events: Sequence[Event], world_key: str | None) -> None:
        async with self._telemetry.sessions() as session, session.begin():
            for item in events:
                data = json.loads(json.dumps(item.payload, default=str))
                await session.merge(
                    LiveEventRow(id=item.id, timestamp_ms=int(item.at.timestamp() * MILLISECONDS), kind=item.kind.value, data=data, world_key=world_key)
                )

    async def prune_events(self, keep: int) -> int:
        async with self._telemetry.sessions() as session, session.begin():
            top = await session.scalar(select(func.max(LiveEventRow.id)))
            if top is None:
                return 0
            result = await session.execute(delete(LiveEventRow).where(LiveEventRow.id <= int(top) - keep))
            return int(getattr(result, "rowcount", 0) or 0)

    async def load_events(self, limit: int, world_key: str | None) -> list[Event]:
        if world_key is None:
            return []
        async with self._telemetry.sessions() as session:
            statement = select(LiveEventRow).where(LiveEventRow.world_key == world_key).order_by(LiveEventRow.id.desc()).limit(limit)
            rows = list(await session.scalars(statement))
        return [
            Event(id=row.id, kind=EventKind(row.kind), payload=row.data, at=datetime.fromtimestamp(row.timestamp_ms / MILLISECONDS, UTC))
            for row in reversed(rows)
            if row.kind in EVENT_KIND_VALUES
        ]

    async def summary(self, epochs: int) -> MetricsSummary:
        slow_ms = self._rules().metrics.slow_call_seconds * MILLISECONDS
        async with self._telemetry.sessions() as session:
            return MetricsSummary(
                totals=await self._totals(session),
                epochs=await self._epochs(session, epochs, slow_ms),
                models=await self._models(session),
                steps=await self._steps(session),
                slowest=list(
                    await session.scalars(
                        select(LlmCallRow).where(LlmCallRow.duration_ms > slow_ms).order_by(LlmCallRow.duration_ms.desc()).limit(SLOWEST_SHOWN)
                    )
                ),
                latest_errors=list(
                    await session.scalars(
                        select(LlmCallRow).where(LlmCallRow.status == LlmCallStatus.ERROR).order_by(LlmCallRow.id.desc()).limit(LATEST_ERRORS_SHOWN)
                    )
                ),
                slow_threshold_ms=slow_ms,
            )

    async def _totals(self, session: AsyncSession) -> Totals:
        row = (
            await session.execute(
                select(
                    func.count(),
                    func.coalesce(func.sum(LlmCallRow.duration_ms), 0),
                    func.coalesce(func.sum(LlmCallRow.cost_usd), 0.0),
                    func.coalesce(func.sum(LlmCallRow.input_tokens), 0),
                    func.coalesce(func.sum(LlmCallRow.output_tokens), 0),
                )
            )
        ).one()
        return Totals(int(row[0]), int(row[1]), float(row[2]), int(row[3]), int(row[4]))

    async def _epochs(self, session: AsyncSession, count: int, slow_ms: int) -> list[EpochMetrics]:
        statement = (
            select(
                LlmCallRow.epoch,
                func.count(),
                func.sum(LlmCallRow.duration_ms),
                func.sum(LlmCallRow.input_tokens),
                func.sum(LlmCallRow.output_tokens),
                func.sum(LlmCallRow.cost_usd),
                func.sum(case((LlmCallRow.status == LlmCallStatus.ERROR, 1), else_=0)),
                func.sum(case((LlmCallRow.attempts > 1, 1), else_=0)),
                func.sum(case((LlmCallRow.duration_ms > slow_ms, 1), else_=0)),
            )
            .where(LlmCallRow.epoch.is_not(None))
            .group_by(LlmCallRow.epoch)
            .order_by(LlmCallRow.epoch.desc())
            .limit(count)
        )
        return [
            EpochMetrics(
                int(row[0]),
                int(row[1]),
                int(row[2] or 0),
                int(row[3] or 0),
                int(row[4] or 0),
                float(row[5] or 0),
                int(row[6] or 0),
                int(row[7] or 0),
                int(row[8] or 0),
            )
            for row in await session.execute(statement)
        ]

    async def _models(self, session: AsyncSession) -> list[ModelMetrics]:
        statement = select(
            LlmCallRow.model,
            func.count(),
            func.sum(LlmCallRow.duration_ms),
            func.sum(LlmCallRow.input_tokens),
            func.sum(LlmCallRow.output_tokens),
            func.sum(LlmCallRow.cost_usd),
        ).group_by(LlmCallRow.model)
        rows = await session.execute(statement)
        return [
            ModelMetrics(
                str(row[0]), int(row[1]), int(row[2] or 0), int((row[2] or 0) // max(1, row[1])), int(row[3] or 0), int(row[4] or 0), float(row[5] or 0)
            )
            for row in rows
        ]

    async def _steps(self, session: AsyncSession) -> list[StepMetrics]:
        grouped: dict[str, list[LlmCallRow]] = {}
        for row in await session.scalars(select(LlmCallRow)):
            grouped.setdefault(step_group(row.job), []).append(row)
        steps = [
            StepMetrics(
                step=name,
                calls=len(rows),
                average_ms=sum(row.duration_ms for row in rows) // len(rows),
                longest_ms=max(row.duration_ms for row in rows),
                cost=sum(row.cost_usd for row in rows),
                errors=sum(1 for row in rows if row.status is LlmCallStatus.ERROR),
            )
            for name, rows in grouped.items()
        ]
        return sorted(steps, key=lambda step: step.average_ms * step.calls, reverse=True)

    async def estimate(self, *, started_at: datetime | None, phase: int | None, phase_started_at: datetime | None) -> EpochEstimate:
        async with self._telemetry.sessions() as session:
            rows = list(
                await session.scalars(
                    select(LiveEventRow)
                    .where(LiveEventRow.kind.in_([EventKind.EPOCH_PROGRESS.value, EventKind.EPOCH_FINISHED.value]))
                    .order_by(LiveEventRow.id.desc())
                    .limit(ETA_EVENTS)
                )
            )
        records: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        for row in reversed(rows):
            data = row.data
            if row.kind == EventKind.EPOCH_PROGRESS.value and isinstance(data.get("phase"), int) and isinstance(data.get("seconds"), int | float):
                if data["phase"] == 1 or current is None:
                    current = {"phases": {}}
                    records.append(current)
                current["phases"][int(data["phase"])] = float(data["seconds"])
            elif row.kind == EventKind.EPOCH_FINISHED.value and current is not None and isinstance(data.get("seconds"), int | float):
                current["total"] = float(data["seconds"])
                current = None
        finished = [record for record in records if "total" in record][-self._rules().metrics.eta_average_epochs :]
        now = datetime.now(UTC)
        elapsed = int((now - started_at).total_seconds()) if started_at is not None else None
        if not finished:
            return EpochEstimate(0, None, {}, started_at is not None, elapsed, None, phase, False)
        average_total = sum(record["total"] for record in finished) / len(finished)
        starts: dict[int, int] = {}
        for number in range(1, 6):
            values = [record["phases"][number] for record in finished if number in record["phases"]]
            if values:
                starts[number] = round(sum(values) / len(values))
        estimate: float | None = None
        if elapsed is not None:
            if phase is not None and phase in starts and phase_started_at is not None and started_at is not None:
                in_phase = (now - phase_started_at).total_seconds()
                estimate = average_total - starts[phase] - max(0.0, in_phase)
            else:
                estimate = average_total - elapsed
        return EpochEstimate(
            samples=len(finished),
            average_epoch_seconds=round(average_total),
            average_phase_starts=starts,
            running=started_at is not None,
            elapsed_seconds=elapsed,
            remaining_seconds=max(0, round(estimate)) if estimate is not None else None,
            phase=phase,
            overrun=estimate is not None and estimate < 0,
        )

    def uptime_seconds(self) -> int:
        return int(time.monotonic() - self._started)


def health(
    *,
    rules: Rules,
    ring: ErrorRing,
    database_path: Path,
    log_file: Path,
    latest_backup: tuple[str, datetime] | None,
    backup_count: int,
    running_jobs: int,
    read_only: bool,
    uptime_seconds: int,
) -> HealthReport:
    check = quick_check(database_path) if database_path.is_file() else "missing"
    wal = database_path.with_name(database_path.name + WAL_SUFFIX)
    window = datetime.now(UTC) - timedelta(minutes=rules.server.health_error_minutes)
    if check != QUICK_CHECK_OK:
        status = HealthStatus.BAD
    elif ring.errors_since(window):
        status = HealthStatus.WARNING
    else:
        status = HealthStatus.OK
    age = int((datetime.now(UTC) - latest_backup[1]).total_seconds() // 60) if latest_backup else None
    return HealthReport(
        status=status,
        version=APP_VERSION,
        uptime_seconds=uptime_seconds,
        database=DatabaseHealth(
            file=database_path.name,
            size=database_path.stat().st_size if database_path.is_file() else 0,
            wal_size=wal.stat().st_size if wal.is_file() else 0,
            quick_check=check,
        ),
        latest_backup=latest_backup[0] if latest_backup else None,
        latest_backup_age_minutes=age,
        backup_count=backup_count,
        running_jobs=running_jobs,
        read_only=read_only,
        log_file=str(log_file),
        recent_errors=ring.recent(rules.server.health_errors_shown),
    )
