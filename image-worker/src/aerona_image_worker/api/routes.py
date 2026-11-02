from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, Response, status
from sse_starlette import EventSourceResponse, ServerSentEvent

from aerona_image_worker.api.schemas import HealthResponse, JobAccepted, JobEventView, JobRequest, JobView
from aerona_image_worker.constants.defaults import SSE_PING_SECONDS
from aerona_image_worker.constants.http import HEALTH_PATH, JOB_EVENTS_PATH, JOB_IMAGE_PATH, JOB_PATH, JOBS_PATH, LAST_EVENT_ID_HEADER, PNG_MEDIA_TYPE
from aerona_image_worker.domain.enums import JobStatus
from aerona_image_worker.domain.generation import GenerationRequest
from aerona_image_worker.errors import ImageNotReadyError
from aerona_image_worker.jobs.job import Job
from aerona_image_worker.jobs.scheduler import JobOverrides, JobScheduler
from aerona_image_worker.settings import Settings

router = APIRouter()


def scheduler_of(request: Request) -> JobScheduler:
    scheduler: JobScheduler = request.app.state.scheduler
    return scheduler


def settings_of(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


SchedulerDep = Annotated[JobScheduler, Depends(scheduler_of)]
SettingsDep = Annotated[Settings, Depends(settings_of)]


@router.get(HEALTH_PATH, response_model=HealthResponse)
async def health(scheduler: SchedulerDep, settings: SettingsDep) -> HealthResponse:
    running = scheduler.running_job
    return HealthResponse(
        status="ok",
        backend=settings.backend,
        model_id=settings.resolved_model_id,
        loaded=scheduler.loaded,
        loading=scheduler.loading,
        queue_length=scheduler.queue_length,
        running_job_id=running.job_id if running else None,
        idle_unload_seconds=scheduler.idle_unload_seconds,
    )


@router.post(JOBS_PATH, response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def enqueue(body: JobRequest, scheduler: SchedulerDep) -> JobAccepted:
    job = scheduler.submit(
        GenerationRequest(prompt=body.prompt, width=body.width, height=body.height, steps=body.steps, seed=body.seed),
        body.priority,
        JobOverrides(
            load_timeout_seconds=body.load_timeout_seconds,
            image_timeout_seconds=body.image_timeout_seconds,
            idle_unload_seconds=body.idle_unload_seconds,
        ),
    )
    return JobAccepted(job_id=job.job_id, status=job.status, position=scheduler.position(job))


@router.get(JOB_PATH, response_model=JobView)
async def job_status(job_id: str, scheduler: SchedulerDep) -> JobView:
    job = scheduler.get(job_id)
    return JobView.of(job, scheduler.position(job))


@router.get(JOB_EVENTS_PATH)
async def job_events(
    job_id: str,
    scheduler: SchedulerDep,
    last_event_id: Annotated[str | None, Header(alias=LAST_EVENT_ID_HEADER)] = None,
) -> EventSourceResponse:
    job = scheduler.get(job_id)
    after = int(last_event_id) if last_event_id and last_event_id.isdigit() else 0
    return EventSourceResponse(stream_events(job, after), ping=SSE_PING_SECONDS)


async def stream_events(job: Job, after: int) -> AsyncIterator[ServerSentEvent]:
    async for event in job.follow(after):
        view = JobEventView.of(job.job_id, event)
        yield ServerSentEvent(data=view.model_dump_json(), event=event.kind.value, id=str(event.sequence))


@router.get(JOB_IMAGE_PATH, response_class=Response, responses={200: {"content": {PNG_MEDIA_TYPE: {}}}})
async def job_image(job_id: str, scheduler: SchedulerDep) -> Response:
    job = scheduler.get(job_id)
    if job.status is not JobStatus.DONE or job.image is None:
        raise ImageNotReadyError(f"image job {job_id} is {job.status.value}; no image is available")
    return Response(content=job.image, media_type=PNG_MEDIA_TYPE)


@router.delete(JOB_PATH, status_code=status.HTTP_204_NO_CONTENT)
async def cancel_job(job_id: str, scheduler: SchedulerDep) -> Response:
    scheduler.cancel(job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
