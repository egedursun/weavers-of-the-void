import asyncio
import contextlib
import secrets
import shutil
import time
from collections.abc import Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aerona.constants.library_packages import LIBRARY_JOB_ID_BYTES, LIBRARY_JOB_KEEP_SECONDS, LIBRARY_PROGRESS_STEP
from aerona.core.account_scope import current_account, current_workspace, detached
from aerona.core.errors import NotFoundError
from aerona.domain.enums.library_jobs import LibraryJobKind, LibraryJobStage, LibraryJobStatus, LibraryStreamKind
from aerona.services.library.feed import LibraryFeed
from aerona.services.library.package import PackagePreview

NO_SUCH_JOB = "No such library job."
EXPORT_RUNNING = "an export of it is running"
IMPORT_RUNNING = "an import into it is running"


@dataclass
class LibraryJob:
    id: str
    kind: LibraryJobKind
    stage: LibraryJobStage
    universe_id: str | None
    universe_name: str
    status: LibraryJobStatus = LibraryJobStatus.RUNNING
    done: int = 0
    total: int = 0
    error: str = ""
    notes: list[str] = field(default_factory=list)
    file_name: str = ""
    size_bytes: int = 0
    file: Path | None = None
    folder: Path | None = None
    preview: PackagePreview | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished: float | None = None
    task: asyncio.Task[Any] | None = None
    shown: float = 0.0
    started_by: int | None = None
    workspace_id: int | None = None

    @property
    def progress(self) -> float:
        if self.status is LibraryJobStatus.DONE:
            return 1.0
        return min(1.0, self.done / self.total) if self.total > 0 else 0.0

    @property
    def active(self) -> bool:
        return self.status is LibraryJobStatus.RUNNING


def remove_quietly(path: Path | None) -> None:
    if path is None:
        return
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)


class LibraryJobs:
    def __init__(self, feed: LibraryFeed) -> None:
        self._feed = feed
        self._jobs: dict[str, LibraryJob] = {}

    def every(self) -> list[LibraryJob]:
        return sorted(self._jobs.values(), key=lambda job: (job.created_at, job.id), reverse=True)

    def of_universe(self, universe_id: str) -> list[LibraryJob]:
        return [job for job in self.every() if job.universe_id == universe_id]

    def find(self, job_id: str | None) -> LibraryJob | None:
        return self._jobs.get(job_id) if job_id is not None else None

    def get(self, job_id: str, kind: LibraryJobKind | None = None) -> LibraryJob:
        found = self.find(job_id)
        if found is None or (kind is not None and found.kind is not kind):
            raise NotFoundError(NO_SUCH_JOB)
        return found

    def busy_reason(self, universe_id: str) -> str | None:
        for job in self._jobs.values():
            if job.universe_id == universe_id and job.active:
                return EXPORT_RUNNING if job.kind is LibraryJobKind.EXPORT else IMPORT_RUNNING
        return None

    def begin(self, kind: LibraryJobKind, stage: LibraryJobStage, universe_id: str | None, universe_name: str) -> LibraryJob:
        account = current_account()
        job = LibraryJob(
            id=secrets.token_hex(LIBRARY_JOB_ID_BYTES),
            kind=kind,
            stage=stage,
            universe_id=universe_id,
            universe_name=universe_name,
            started_by=account.id if account is not None else None,
            workspace_id=current_workspace(),
        )
        self._jobs[job.id] = job
        self.announce(job)
        return job

    def run(self, job: LibraryJob, work: Coroutine[Any, Any, None]) -> None:
        job.task = detached(work)

    def announce(self, job: LibraryJob) -> None:
        job.updated_at = datetime.now(UTC)
        job.shown = job.progress
        self._feed.publish(LibraryStreamKind.JOB, universe_id=job.universe_id, job_id=job.id)

    def enter(self, job: LibraryJob, stage: LibraryJobStage, total: int = 0) -> None:
        job.stage, job.done, job.total = stage, 0, total
        self.announce(job)

    def advance(self, job: LibraryJob, done: int, total: int) -> None:
        job.done, job.total = done, total
        if job.progress - job.shown >= LIBRARY_PROGRESS_STEP or done >= total:
            self.announce(job)

    def wait(self, job: LibraryJob) -> None:
        job.status = LibraryJobStatus.WAITING
        self.announce(job)

    def resume(self, job: LibraryJob, stage: LibraryJobStage) -> None:
        job.status = LibraryJobStatus.RUNNING
        self.enter(job, stage)

    def finish(self, job: LibraryJob, status: LibraryJobStatus, error: str = "") -> None:
        job.status, job.error, job.finished = status, error, time.monotonic()
        self.announce(job)

    def forget(self, job: LibraryJob) -> None:
        self._jobs.pop(job.id, None)
        remove_quietly(job.file)
        remove_quietly(job.folder)
        job.file = None
        job.folder = None

    def expire(self, keep_seconds: float = LIBRARY_JOB_KEEP_SECONDS) -> list[str]:
        now = time.monotonic()
        stale = [
            job
            for job in self._jobs.values()
            if (job.finished is not None and now - job.finished >= keep_seconds)
            or (job.status is LibraryJobStatus.WAITING and (datetime.now(UTC) - job.updated_at).total_seconds() >= keep_seconds)
        ]
        for job in stale:
            self.forget(job)
        return [job.id for job in stale]

    async def stop(self) -> None:
        tasks = [job.task for job in self._jobs.values() if job.task is not None and not job.task.done()]
        for task in tasks:
            task.cancel()
        with contextlib.suppress(Exception):
            await asyncio.gather(*tasks, return_exceptions=True)
        for job in list(self._jobs.values()):
            self.forget(job)
