import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime

from aerona_image_worker.constants.limits import EXTRA_PROGRESS_UNITS, PERCENT_SCALE
from aerona_image_worker.domain.enums import TERMINAL_EVENTS, TERMINAL_STATUSES, EventKind, JobPriority, JobStatus
from aerona_image_worker.domain.generation import GenerationRequest


@dataclass(frozen=True)
class JobTimeouts:
    load_seconds: float
    image_seconds: float


@dataclass(frozen=True)
class JobEvent:
    sequence: int
    kind: EventKind
    step: int
    total: int
    percent: int
    position: int | None
    message: str | None
    at: datetime


def progress_percent(kind: EventKind, step: int, total: int) -> int:
    units = total + EXTRA_PROGRESS_UNITS
    if kind is EventKind.DONE:
        return PERCENT_SCALE
    if kind is EventKind.STEP:
        return round(PERCENT_SCALE * (1 + step) / units)
    if kind is EventKind.DECODING:
        return round(PERCENT_SCALE * (1 + total) / units)
    return 0


class Job:
    def __init__(self, job_id: str, request: GenerationRequest, priority: JobPriority, timeouts: JobTimeouts) -> None:
        self.job_id = job_id
        self.request = request
        self.priority = priority
        self.timeouts = timeouts
        self.status = JobStatus.QUEUED
        self.created_at = datetime.now(UTC)
        self.started_at: datetime | None = None
        self.finished_at: datetime | None = None
        self.image: bytes | None = None
        self.error: str | None = None
        self.events: list[JobEvent] = []
        self._signal = asyncio.Event()

    @property
    def finished(self) -> bool:
        return self.status in TERMINAL_STATUSES

    @property
    def last_event(self) -> JobEvent | None:
        return self.events[-1] if self.events else None

    def publish(self, kind: EventKind, step: int = 0, total: int = 0, *, position: int | None = None, message: str | None = None) -> None:
        if self.finished:
            return
        total = total or self.request.steps
        event = JobEvent(
            sequence=len(self.events) + 1,
            kind=kind,
            step=step,
            total=total,
            percent=progress_percent(kind, step, total),
            position=position,
            message=message,
            at=datetime.now(UTC),
        )
        self.events.append(event)
        signal, self._signal = self._signal, asyncio.Event()
        signal.set()

    def report(self, kind: EventKind, step: int, total: int) -> None:
        self.publish(kind, step, total)

    def start(self) -> None:
        self.status = JobStatus.RUNNING
        self.started_at = datetime.now(UTC)

    def complete(self, image: bytes) -> None:
        self.image = image
        self._finish(JobStatus.DONE, EventKind.DONE, None)

    def fail(self, message: str) -> None:
        self.error = message
        self._finish(JobStatus.ERROR, EventKind.ERROR, message)

    def cancel(self) -> None:
        self._finish(JobStatus.CANCELLED, EventKind.CANCELLED, None)

    def _finish(self, status: JobStatus, kind: EventKind, message: str | None) -> None:
        if self.finished:
            return
        step = self.request.steps if kind is EventKind.DONE else 0
        self.publish(kind, step, self.request.steps, message=message)
        self.status = status
        self.finished_at = datetime.now(UTC)

    async def follow(self, after: int = 0) -> AsyncIterator[JobEvent]:
        index = max(0, after)
        while True:
            while index < len(self.events):
                event = self.events[index]
                index += 1
                yield event
                if event.kind in TERMINAL_EVENTS:
                    return
            if self.finished:
                return
            await self._signal.wait()
