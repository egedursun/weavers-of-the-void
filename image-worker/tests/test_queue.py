import asyncio

from aerona_image_worker.backends.base import BackendSpec
from aerona_image_worker.backends.factory import build_backend
from aerona_image_worker.domain.enums import BackendName, JobPriority, JobStatus
from aerona_image_worker.domain.generation import GenerationRequest
from aerona_image_worker.jobs.job import Job, JobTimeouts
from aerona_image_worker.jobs.queue import JobQueue
from aerona_image_worker.jobs.scheduler import JobScheduler, SchedulerDefaults
from aerona_image_worker.runtime.inline import InlineRunner

REQUEST = GenerationRequest(prompt="a quiet harbour", width=256, height=256, steps=2, seed=1)
TIMEOUTS = JobTimeouts(load_seconds=1.0, image_seconds=1.0)


def make_job(name: str, priority: JobPriority) -> Job:
    return Job(name, REQUEST, priority, TIMEOUTS)


async def test_manual_jobs_jump_ahead_of_bulk_jobs_and_keep_fifo_within_a_class() -> None:
    queue = JobQueue()
    arrivals = [("bulk-1", JobPriority.BULK), ("manual-1", JobPriority.MANUAL), ("bulk-2", JobPriority.BULK), ("manual-2", JobPriority.MANUAL)]
    for name, priority in arrivals:
        queue.push(make_job(name, priority))
    order = [(await queue.pop()).job_id for _ in range(4)]
    assert order == ["manual-1", "manual-2", "bulk-1", "bulk-2"]


async def test_removed_job_is_skipped_and_positions_follow_priority() -> None:
    queue = JobQueue()
    bulk, manual, other = make_job("bulk", JobPriority.BULK), make_job("manual", JobPriority.MANUAL), make_job("other", JobPriority.BULK)
    for job in (bulk, manual, other):
        queue.push(job)
    assert [queue.position(job) for job in (manual, bulk, other)] == [0, 1, 2]
    assert queue.remove(bulk) is True
    assert queue.remove(bulk) is False
    assert queue.position(bulk) is None
    assert [(await queue.pop()).job_id for _ in range(2)] == ["manual", "other"]
    assert len(queue) == 0


async def test_pop_waits_until_a_job_arrives() -> None:
    queue = JobQueue()
    waiter = asyncio.create_task(queue.pop())
    await asyncio.sleep(0.01)
    assert not waiter.done()
    queue.push(make_job("late", JobPriority.BULK))
    assert (await asyncio.wait_for(waiter, 1.0)).job_id == "late"


async def test_scheduler_runs_one_job_at_a_time_in_priority_order() -> None:
    spec = BackendSpec(name=BackendName.FAKE, model_id="fake", fake_step_seconds=0.01)
    scheduler = JobScheduler(InlineRunner(spec, build_backend), SchedulerDefaults(5.0, 5.0, 0.0, 16))
    jobs = [
        scheduler.submit(REQUEST, JobPriority.BULK),
        scheduler.submit(REQUEST, JobPriority.BULK),
        scheduler.submit(REQUEST, JobPriority.MANUAL),
    ]
    scheduler.start()
    try:
        for job in jobs:
            async for _event in job.follow():
                pass
    finally:
        await scheduler.stop()
    assert all(job.status is JobStatus.DONE for job in jobs)
    started = sorted(jobs, key=lambda job: job.started_at or job.created_at)
    assert started == [jobs[2], jobs[0], jobs[1]]
    finished = [job.finished_at for job in started]
    starts = [job.started_at for job in started]
    assert all(previous is not None and following is not None and previous <= following for previous, following in zip(finished, starts[1:], strict=False))
