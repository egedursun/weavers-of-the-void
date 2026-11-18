import asyncio
from pathlib import Path

import pytest

from aerona.core.errors import BusyError
from aerona.db.session import Database
from aerona.domain.enums.job import JobKind, JobStatus
from aerona.events.bus import EventBus
from aerona.jobs.context import JobContext
from aerona.jobs.manager import JobManager
from tests.conftest import OpenDatabase
from tests.polling import until


async def build_manager(tmp_path: Path, open_database: OpenDatabase) -> tuple[JobManager, Database]:
    database = open_database(tmp_path / "jobs.db")
    return JobManager(database, EventBus()), database


async def wait_for_status(manager: JobManager, job_id: str, status: JobStatus) -> None:
    async def reached() -> bool:
        return bool((await manager.get(job_id)).status == status.value)

    if not await until(reached):
        raise AssertionError(f"job never reached {status}")


async def test_job_runs_and_records_result(tmp_path: Path, open_database: OpenDatabase) -> None:
    manager, database = await build_manager(tmp_path, open_database)

    async def handler(context: JobContext) -> dict[str, int]:
        context.report(0.5, "halfway")
        return {"answer": 42}

    job_id = await manager.submit(JobKind.SIMULATION, handler)
    await wait_for_status(manager, job_id, JobStatus.SUCCEEDED)
    row = await manager.get(job_id)
    assert row.result == {"answer": 42}
    assert row.progress == 1.0
    await database.dispose()


async def test_exclusive_group_blocks_second_job_and_cancel_works(tmp_path: Path, open_database: OpenDatabase) -> None:
    manager, database = await build_manager(tmp_path, open_database)
    started = asyncio.Event()

    async def slow(_context: JobContext) -> None:
        started.set()
        await asyncio.sleep(10)

    job_id = await manager.submit(JobKind.EPOCH, slow, exclusive_group="world")
    await started.wait()
    with pytest.raises(BusyError):
        await manager.submit(JobKind.EPOCH, slow, exclusive_group="world")
    await manager.cancel(job_id)
    await wait_for_status(manager, job_id, JobStatus.CANCELLED)
    assert manager.busy_group("world") is None
    await database.dispose()


async def test_failed_job_records_error(tmp_path: Path, open_database: OpenDatabase) -> None:
    manager, database = await build_manager(tmp_path, open_database)

    async def broken(_context: JobContext) -> None:
        raise RuntimeError("boom")

    job_id = await manager.submit(JobKind.SIMULATION, broken)
    await wait_for_status(manager, job_id, JobStatus.FAILED)
    assert (await manager.get(job_id)).error == "boom"
    await database.dispose()


async def test_jobs_beyond_the_capacity_wait_in_the_queue(tmp_path: Path, open_database: OpenDatabase) -> None:
    jobs, _ = await build_manager(tmp_path, open_database)
    jobs.bind_capacity(lambda: 1)
    release = asyncio.Event()
    started: list[str] = []

    async def slow(context: JobContext) -> dict[str, object] | None:
        started.append(context.job_id)
        await release.wait()
        return None

    first = await jobs.submit(JobKind.EPOCH, slow)
    second = await jobs.submit(JobKind.EPOCH, slow)
    await asyncio.sleep(0.05)
    assert started == [first]
    assert jobs.queued_count == 1
    release.set()
    await asyncio.sleep(0.05)
    assert started == [first, second]


async def test_a_duplicate_key_returns_the_running_job(tmp_path: Path, open_database: OpenDatabase) -> None:
    jobs, _ = await build_manager(tmp_path, open_database)
    release = asyncio.Event()

    async def slow(context: JobContext) -> dict[str, object] | None:
        await release.wait()
        return None

    first = await jobs.submit(JobKind.EPOCH, slow, dedupe_key="deepen:7")
    assert await jobs.submit(JobKind.EPOCH, slow, dedupe_key="deepen:7") == first
    release.set()
