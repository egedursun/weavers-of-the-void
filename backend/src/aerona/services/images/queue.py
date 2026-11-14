import asyncio
import logging
import secrets
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.image_styles import styled_prompt
from aerona.core.activity import ActivityLog, collecting
from aerona.core.errors import ConflictError, NotFoundError, ValidationFailedError
from aerona.core.grammar import several
from aerona.db.session import Database
from aerona.domain.enums.job import JobKind, JobStatus
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.imaging.client import ImageWorkerClient
from aerona.imaging.contract import ImageJobRequest, ImagePriority, ImageProgress, ImageStage
from aerona.imaging.errors import ImageWorkerError
from aerona.jobs.context import JOB_LABEL_KEY, JobContext
from aerona.jobs.manager import JobManager
from aerona.rules.registry import Rules
from aerona.services.images.records import (
    ImageRecords,
    ImageTarget,
    cover_in_style,
    has_image,
    missing_targets,
    resolve_target,
    restyle_targets,
    world_style,
)
from aerona.services.lore_ports import ImagePromptWriter

logger = logging.getLogger(__name__)
TrackedJob = tuple[JobContext, ActivityLog]

SEED_BITS = 31
PERCENT = 100
DISABLED_REASON = "Image generation is off: no image worker is configured (IMAGE_WORKER_URL)."
READ_ONLY_REASON = "Image generation is paused while a guest world is open."


class ImageClass(StrEnum):
    MANUAL = "manual"
    BULK = "bulk"
    AUTO = "auto"
    RESTYLE = "restyle"


class Stage(StrEnum):
    PREPARE = "prepare"
    PROMPT = "prompt"
    LOADING = "loading"
    ENCODING = "encoding"
    STEPS = "steps"
    DECODING = "decoding"
    DONE = "done"


class LogLevel(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class QueuedImage:
    node_id: int
    image_class: ImageClass
    queued_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class BulkRun:
    running: bool = False
    stop_requested: bool = False
    auto: bool = False
    restyle: bool = False
    total: int = 0
    done: int = 0
    failed: int = 0
    skipped: int = 0
    started: datetime | None = None
    finished: datetime | None = None
    rerun_requested: bool = False

    @property
    def remaining(self) -> int:
        return max(0, self.total - self.done - self.failed - self.skipped)


@dataclass(frozen=True)
class LogLine:
    level: LogLevel
    at: datetime
    text: str


@dataclass(frozen=True)
class QueueStatus:
    available: bool
    reason: str | None
    current: QueuedImage | None
    queue: list[QueuedImage]
    bulk: BulkRun
    width: int
    height: int
    steps: int
    log: list[LogLine]


def stage_units(progress: ImageProgress, steps: int) -> tuple[Stage, int]:
    if progress.kind is ImageStage.LOADING:
        return Stage.LOADING, 0
    if progress.kind is ImageStage.ENCODING:
        return Stage.ENCODING, 1
    if progress.kind is ImageStage.STEP:
        return Stage.STEPS, 1 + min(steps, progress.step)
    if progress.kind is ImageStage.DECODING:
        return Stage.DECODING, steps + 1
    if progress.kind is ImageStage.DONE:
        return Stage.DONE, steps + 2
    return Stage.PREPARE, 0


def percent(units: int, steps: int) -> int:
    return round(units * PERCENT / (steps + 2))


class ImageQueue:
    def __init__(
        self,
        database: Database,
        client: ImageWorkerClient,
        records: ImageRecords,
        rules: Callable[[], Rules],
        *,
        bus: EventBus | None = None,
        prompts: ImagePromptWriter | None = None,
        read_only: Callable[[], bool] = lambda: False,
        jobs: JobManager | None = None,
    ) -> None:
        self._database = database
        self._client = client
        self._records = records
        self._rules = rules
        self._bus = bus
        self._prompts = prompts
        self._read_only = read_only
        self._jobs = jobs
        self._manual: deque[QueuedImage] = deque()
        self._background: deque[QueuedImage] = deque()
        self._current: QueuedImage | None = None
        self._worker: asyncio.Task[None] | None = None
        self._bulk_task: asyncio.Task[None] | None = None
        self.bulk = BulkRun()
        self._log: deque[LogLine] = deque(maxlen=rules().image_gen.log_lines)
        self._idle = asyncio.Event()
        self._idle.set()
        self._gpu = asyncio.Lock()

    @property
    def available(self) -> bool:
        return self._client.enabled and not self._read_only()

    def unavailable_reason(self) -> str | None:
        if not self._client.enabled:
            return DISABLED_REASON
        if self._read_only():
            return READ_ONLY_REASON
        return None

    def _publish(self, kind: EventKind, payload: dict[str, Any]) -> None:
        if self._bus is not None:
            self._bus.publish(kind, payload)

    def log(self, level: LogLevel, text: str) -> None:
        line = LogLine(level, datetime.now(UTC), text)
        if self._log.maxlen != self._rules().image_gen.log_lines:
            self._log = deque(self._log, maxlen=self._rules().image_gen.log_lines)
        self._log.append(line)
        self._publish(EventKind.IMAGE_BULK_LOG, {"level": level.value, "text": text, **self._bulk_payload()})

    def _bulk_payload(self) -> dict[str, Any]:
        bulk = self.bulk
        return {"running": bulk.running, "total": bulk.total, "done": bulk.done, "failed": bulk.failed, "skipped": bulk.skipped, "remaining": bulk.remaining}

    def queued(self) -> list[QueuedImage]:
        return [*self._manual, *self._background]

    def _is_queued(self, node_id: int) -> bool:
        return (self._current is not None and self._current.node_id == node_id) or any(item.node_id == node_id for item in self.queued())

    async def enqueue(self, node_id: int, image_class: ImageClass = ImageClass.MANUAL) -> QueuedImage:
        reason = self.unavailable_reason()
        if reason is not None:
            raise ConflictError(reason)
        async with self._database.read() as session:
            target = await resolve_target(session, node_id)
        if self._is_queued(node_id):
            raise ConflictError(f"{target.name} is already waiting for an image.")
        if not target.image_prompt and self._prompts is None:
            raise ValidationFailedError(f"{target.name} has no image prompt yet.")
        item = QueuedImage(node_id, image_class)
        (self._manual if image_class is ImageClass.MANUAL else self._background).append(item)
        position = self.queued().index(item) + (1 if self._current else 0)
        self._publish(EventKind.IMAGE_QUEUED, {"node_id": node_id, "position": position, "class": image_class.value})
        self._ensure_worker()
        return item

    def _ensure_worker(self) -> None:
        if self._worker is None or self._worker.done():
            self._idle.clear()
            self._worker = asyncio.create_task(self._run())

    async def _run(self) -> None:
        try:
            while self._manual or self._background:
                item = self._manual.popleft() if self._manual else self._background.popleft()
                self._current = item
                try:
                    await self._generate_tracked(item)
                except Exception as error:
                    logger.exception("image generation for %s failed", item.node_id)
                    self._publish(EventKind.IMAGE_FAILED, {"node_id": item.node_id, "error": str(error)})
                finally:
                    self._current = None
        finally:
            self._idle.set()

    async def wait_idle(self) -> None:
        await self._idle.wait()

    async def _target(self, node_id: int) -> ImageTarget | None:
        async with self._database.read() as session:
            try:
                return await resolve_target(session, node_id)
            except NotFoundError:
                return None

    async def _generate_tracked(self, item: QueuedImage) -> int | None:
        if self._jobs is None:
            return await self._generate(item)
        target = await self._target(item.node_id)
        name = target.name if target is not None else str(item.node_id)
        context, log = await self._jobs.begin_external(JobKind.IMAGE, {JOB_LABEL_KEY: f"image of {name}", "node_id": item.node_id})
        try:
            with collecting(log):
                created = await self._generate(item)
        except Exception as error:
            await self._jobs.end_external(context, log, JobStatus.FAILED, error=str(error))
            raise
        await self._jobs.end_external(context, log, JobStatus.SUCCEEDED, {"image_id": created})
        return created

    async def _generate(self, item: QueuedImage) -> int | None:
        async with self._gpu:
            return await self._generate_now(item)

    async def _generate_now(self, item: QueuedImage) -> int | None:
        rules = self._rules().image_gen
        steps = rules.steps
        self._publish(EventKind.IMAGE_PROGRESS, {"node_id": item.node_id, "stage": Stage.PREPARE.value, "percent": 0})
        target = await self._target(item.node_id)
        if target is None:
            return None
        prompt = target.image_prompt
        if not prompt and self._prompts is not None:
            self._publish(EventKind.IMAGE_PROGRESS, {"node_id": item.node_id, "stage": Stage.PROMPT.value, "percent": 0})
            prompt = await self._prompts.write_prompt(item.node_id)
        if not prompt:
            raise ValidationFailedError(f"{target.name} has no image prompt.")
        async with self._database.read() as session:
            style = await world_style(session)
        request = ImageJobRequest(
            prompt=styled_prompt(prompt, style.style, style.custom),
            width=rules.width,
            height=rules.height,
            steps=steps,
            seed=secrets.randbits(SEED_BITS),
            priority=ImagePriority.MANUAL if item.image_class is ImageClass.MANUAL else ImagePriority.BULK,
            load_timeout_seconds=rules.startup_timeout_seconds,
            image_timeout_seconds=rules.image_timeout_seconds,
            idle_unload_seconds=rules.idle_unload_seconds,
        )

        async def on_progress(progress: ImageProgress) -> None:
            stage, units = stage_units(progress, steps)
            self._publish(EventKind.IMAGE_PROGRESS, {"node_id": item.node_id, "stage": stage.value, "percent": percent(units, steps), "step": progress.step})

        generated = await self._client.generate(request, on_progress)
        async with self._database.write() as session:
            if await self._target_gone(session, item.node_id):
                self.log(LogLevel.WARNING, f"{target.name} vanished during generation; the image was discarded.")
                return None
            row = await self._records.add_generated(
                session, item.node_id, generated.png, prompt, style=style.signature, cover=item.image_class is ImageClass.RESTYLE
            )
        if row is None:
            return None
        self._publish(EventKind.IMAGE_DONE, {"node_id": item.node_id, "image_id": row.id, "file": row.file_name, "cover": row.is_cover})
        return row.id

    async def _target_gone(self, session: AsyncSession, node_id: int) -> bool:
        try:
            await resolve_target(session, node_id)
        except NotFoundError:
            return True
        return False

    async def start_bulk(self, auto: bool = False, restyle: bool = False) -> BulkRun:
        reason = self.unavailable_reason()
        if reason is not None:
            raise ConflictError(reason)
        if self.bulk.running:
            if auto:
                self.bulk.rerun_requested = True
                return self.bulk
            raise ConflictError("Image generation is already running.")
        async with self._database.read() as session:
            if restyle:
                style = await world_style(session)
                targets = await restyle_targets(session, style.signature)
            else:
                targets = await missing_targets(session)
        if not targets:
            raise ConflictError("Every generated image is already in the world's image style." if restyle else "Every record already has an image.")
        self.bulk = BulkRun(running=True, auto=auto, restyle=restyle, total=len(targets), started=datetime.now(UTC))
        self.log(LogLevel.INFO, f"{'Restyling' if restyle else 'Image generation'} started for {several(len(targets), 'record', 'records')}.")
        tracked = None
        if self._jobs is not None:
            label = (f"restyling of {several(len(targets), 'image', 'images')}" if restyle else f"painting of {several(len(targets), 'image', 'images')}") + (
                " after the epoch" if auto else ""
            )
            tracked = await self._jobs.begin_external(JobKind.IMAGE, {JOB_LABEL_KEY: label, "total": len(targets), "auto": auto})
        self._bulk_task = asyncio.create_task(self._bulk([target.node_id for target in targets], tracked))
        return self.bulk

    def stop_bulk(self) -> BulkRun:
        if not self.bulk.running:
            raise ConflictError("No image generation is running.")
        self.bulk.stop_requested = True
        self.log(LogLevel.INFO, "Stop requested; generation stops after the current image.")
        return self.bulk

    async def wait_bulk(self) -> None:
        if self._bulk_task is not None:
            await self._bulk_task

    def _report_bulk(self, tracked: TrackedJob | None, node_id: int) -> None:
        if tracked is None or self._jobs is None:
            return
        context = tracked[0]
        bulk = self.bulk
        handled = bulk.done + bulk.failed + bulk.skipped
        context.progress = handled / max(1, bulk.total)
        context.stage = f"{handled} of {bulk.total} · record {node_id}"
        self._jobs.report_external(context)

    async def _bulk(self, node_ids: list[int], tracked: TrackedJob | None = None) -> None:
        image_class = ImageClass.RESTYLE if self.bulk.restyle else ImageClass.AUTO if self.bulk.auto else ImageClass.BULK
        log = tracked[1] if tracked is not None else ActivityLog()
        failure: str | None = None
        try:
            with collecting(log):
                for node_id in node_ids:
                    if self.bulk.stop_requested:
                        break
                    await self._bulk_one(node_id, image_class)
                    self._report_bulk(tracked, node_id)
        except Exception as error:
            failure = str(error)
            raise
        finally:
            self.bulk.running = False
            self.bulk.finished = datetime.now(UTC)
            self.log(LogLevel.INFO, f"Done: {self.bulk.done} images, {self.bulk.failed} errors, {self.bulk.skipped} skipped.")
            if tracked is not None and self._jobs is not None:
                status = JobStatus.FAILED if failure else JobStatus.CANCELLED if self.bulk.stop_requested else JobStatus.SUCCEEDED
                summary = {"total": self.bulk.total, "done": self.bulk.done, "failed": self.bulk.failed, "skipped": self.bulk.skipped}
                await self._jobs.end_external(tracked[0], tracked[1], status, summary, failure)
            rerun = self.bulk.rerun_requested and not self.bulk.stop_requested
            if rerun:
                try:
                    await self.start_bulk(auto=True)
                except ConflictError:
                    self.log(LogLevel.INFO, "Nothing left to generate after the epoch ended.")

    async def _bulk_one(self, node_id: int, image_class: ImageClass) -> None:
        target = await self._target(node_id)
        async with self._database.read() as session:
            if image_class is ImageClass.RESTYLE:
                gained = await cover_in_style(session, node_id, (await world_style(session)).signature)
            else:
                gained = await has_image(session, node_id)
        if target is None or gained or (not target.image_prompt and self._prompts is None) or self._is_queued(node_id):
            self.bulk.skipped += 1
            return
        attempts = self._rules().image_gen.retries + 1
        for attempt in range(1, attempts + 1):
            try:
                self._current = QueuedImage(node_id, image_class)
                created = await self._generate(self._current)
            except (ImageWorkerError, ValidationFailedError) as error:
                self.log(LogLevel.WARNING if attempt < attempts else LogLevel.ERROR, f"{target.name}: {error}")
                continue
            finally:
                self._current = None
            if created is None:
                self.bulk.skipped += 1
            else:
                self.bulk.done += 1
                self.log(LogLevel.INFO, f"{target.name}: image ready.")
            return
        self.bulk.failed += 1

    def status(self) -> QueueStatus:
        rules = self._rules().image_gen
        return QueueStatus(
            available=self.available,
            reason=self.unavailable_reason(),
            current=self._current,
            queue=self.queued(),
            bulk=self.bulk,
            width=rules.width,
            height=rules.height,
            steps=rules.steps,
            log=list(self._log),
        )

    async def shutdown(self) -> None:
        for task in (self._worker, self._bulk_task):
            if task is not None and not task.done():
                task.cancel()
