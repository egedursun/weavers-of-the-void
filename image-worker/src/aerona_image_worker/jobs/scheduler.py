import asyncio
import logging
import uuid
from dataclasses import dataclass

from aerona_image_worker.domain.enums import EventKind, JobPriority
from aerona_image_worker.domain.generation import GenerationRequest
from aerona_image_worker.errors import BackendError, JobNotCancellableError
from aerona_image_worker.jobs.job import Job, JobTimeouts
from aerona_image_worker.jobs.queue import JobQueue
from aerona_image_worker.jobs.store import JobStore
from aerona_image_worker.runtime.base import Runner

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SchedulerDefaults:
    load_timeout_seconds: float
    image_timeout_seconds: float
    idle_unload_seconds: float
    retained_jobs: int


@dataclass(frozen=True)
class JobOverrides:
    load_timeout_seconds: float | None = None
    image_timeout_seconds: float | None = None
    idle_unload_seconds: float | None = None


class JobScheduler:
    def __init__(self, runner: Runner, defaults: SchedulerDefaults) -> None:
        self._runner = runner
        self._defaults = defaults
        self._queue = JobQueue()
        self._store = JobStore(defaults.retained_jobs)
        self._idle_unload_seconds = defaults.idle_unload_seconds
        self._running: Job | None = None
        self._loading = False
        self._worker: asyncio.Task[None] | None = None
        self._idle_task: asyncio.Task[None] | None = None
        self._idle_unloading = False

    @property
    def loaded(self) -> bool:
        return self._runner.loaded

    @property
    def loading(self) -> bool:
        return self._loading

    @property
    def queue_length(self) -> int:
        return len(self._queue)

    @property
    def running_job(self) -> Job | None:
        return self._running

    @property
    def idle_unload_seconds(self) -> float:
        return self._idle_unload_seconds

    def start(self) -> None:
        if self._worker is None:
            self._worker = asyncio.create_task(self._work(), name="image-worker-loop")

    async def stop(self) -> None:
        worker, self._worker = self._worker, None
        if worker is not None:
            worker.cancel()
            await asyncio.wait({worker})
        await self._stop_idle_timer()
        await self._runner.unload()

    def submit(self, request: GenerationRequest, priority: JobPriority, overrides: JobOverrides | None = None) -> Job:
        chosen = overrides or JobOverrides()
        timeouts = JobTimeouts(
            load_seconds=chosen.load_timeout_seconds or self._defaults.load_timeout_seconds,
            image_seconds=chosen.image_timeout_seconds or self._defaults.image_timeout_seconds,
        )
        if chosen.idle_unload_seconds is not None:
            self._idle_unload_seconds = chosen.idle_unload_seconds
        job = Job(uuid.uuid4().hex, request, priority, timeouts)
        self._store.add(job)
        self._queue.push(job)
        self._cancel_pending_idle_timer()
        job.publish(EventKind.QUEUED, position=self.position(job))
        return job

    def get(self, job_id: str) -> Job:
        return self._store.get(job_id)

    def position(self, job: Job) -> int | None:
        place = self._queue.position(job)
        if place is None:
            return None
        return place + (1 if self._running is not None else 0)

    def cancel(self, job_id: str) -> Job:
        job = self._store.get(job_id)
        if not self._queue.remove(job):
            raise JobNotCancellableError(f"image job {job_id} is {job.status.value} and can no longer be cancelled")
        job.cancel()
        self._store.prune()
        return job

    async def _work(self) -> None:
        while True:
            job = await self._queue.pop()
            await self._stop_idle_timer()
            await self._execute(job)
            self._arm_idle_timer()

    async def _execute(self, job: Job) -> None:
        self._running = job
        job.start()
        try:
            if not self._runner.loaded:
                job.publish(EventKind.LOADING)
                self._loading = True
                try:
                    await self._runner.ensure_loaded(job.timeouts.load_seconds)
                finally:
                    self._loading = False
            job.complete(await self._runner.generate(job.request, job.timeouts.image_seconds, job.report))
        except BackendError as error:
            logger.warning("image job %s failed: %s", job.job_id, error)
            job.fail(str(error))
        except Exception as error:
            logger.exception("image job %s crashed", job.job_id)
            job.fail(f"{type(error).__name__}: {error}")
        finally:
            self._running = None
            self._store.prune()

    def _arm_idle_timer(self) -> None:
        if len(self._queue) or self._idle_unload_seconds <= 0 or not self._runner.loaded:
            return
        self._idle_task = asyncio.create_task(self._unload_when_idle(self._idle_unload_seconds), name="image-worker-idle")

    async def _unload_when_idle(self, seconds: float) -> None:
        await asyncio.sleep(seconds)
        if len(self._queue) or self._running is not None:
            return
        self._idle_unloading = True
        try:
            await self._runner.unload()
            logger.info("image model released after %.0fs idle", seconds)
        finally:
            self._idle_unloading = False

    def _cancel_pending_idle_timer(self) -> None:
        if self._idle_task is not None and not self._idle_unloading:
            self._idle_task.cancel()

    async def _stop_idle_timer(self) -> None:
        task, self._idle_task = self._idle_task, None
        if task is None:
            return
        if not self._idle_unloading:
            task.cancel()
        await asyncio.wait({task})
