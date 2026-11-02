from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from aerona_image_worker.constants.limits import MAX_DIMENSION, MAX_PROMPT_CHARS, MAX_SEED, MAX_STEPS, MIN_DIMENSION, MIN_STEPS
from aerona_image_worker.domain.enums import BackendName, EventKind, JobPriority, JobStatus
from aerona_image_worker.jobs.job import Job, JobEvent


class HealthResponse(BaseModel):
    status: str
    backend: BackendName
    model_id: str
    loaded: bool
    loading: bool
    queue_length: int
    running_job_id: str | None
    idle_unload_seconds: float


class JobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=MAX_PROMPT_CHARS)
    width: int = Field(ge=MIN_DIMENSION, le=MAX_DIMENSION)
    height: int = Field(ge=MIN_DIMENSION, le=MAX_DIMENSION)
    steps: int = Field(ge=MIN_STEPS, le=MAX_STEPS)
    seed: int = Field(ge=0, le=MAX_SEED)
    priority: JobPriority = JobPriority.BULK
    load_timeout_seconds: float | None = Field(default=None, gt=0)
    image_timeout_seconds: float | None = Field(default=None, gt=0)
    idle_unload_seconds: float | None = Field(default=None, ge=0)


class JobAccepted(BaseModel):
    job_id: str
    status: JobStatus
    position: int | None


class JobEventView(BaseModel):
    job_id: str
    sequence: int
    kind: EventKind
    step: int
    total: int
    percent: int
    position: int | None
    message: str | None
    at: datetime

    @classmethod
    def of(cls, job_id: str, event: JobEvent) -> "JobEventView":
        return cls(
            job_id=job_id,
            sequence=event.sequence,
            kind=event.kind,
            step=event.step,
            total=event.total,
            percent=event.percent,
            position=event.position,
            message=event.message,
            at=event.at,
        )


class JobView(BaseModel):
    job_id: str
    status: JobStatus
    priority: JobPriority
    width: int
    height: int
    steps: int
    seed: int
    position: int | None
    last_event: JobEventView | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    @classmethod
    def of(cls, job: Job, position: int | None) -> "JobView":
        last = job.last_event
        return cls(
            job_id=job.job_id,
            status=job.status,
            priority=job.priority,
            width=job.request.width,
            height=job.request.height,
            steps=job.request.steps,
            seed=job.request.seed,
            position=position,
            last_event=JobEventView.of(job.job_id, last) if last else None,
            error=job.error,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
        )


class ErrorResponse(BaseModel):
    error: str
