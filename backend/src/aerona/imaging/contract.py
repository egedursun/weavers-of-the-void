from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ImagePriority(StrEnum):
    MANUAL = "manual"
    BULK = "bulk"


class ImageJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


class ImageStage(StrEnum):
    QUEUED = "queued"
    LOADING = "loading"
    ENCODING = "encoding"
    STEP = "step"
    DECODING = "decoding"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


TERMINAL_STAGES = frozenset({ImageStage.DONE, ImageStage.ERROR, ImageStage.CANCELLED})


class WorkerModel(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


class ImageJobRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    prompt: str
    width: int
    height: int
    steps: int
    seed: int
    priority: ImagePriority = ImagePriority.BULK
    load_timeout_seconds: float | None = None
    image_timeout_seconds: float | None = None
    idle_unload_seconds: float | None = None


class ImageJobAccepted(WorkerModel):
    job_id: str
    status: ImageJobStatus
    position: int | None = None


class ImageProgress(WorkerModel):
    job_id: str
    sequence: int
    kind: ImageStage
    step: int
    total: int
    percent: int
    position: int | None = None
    message: str | None = None
    at: datetime

    @property
    def terminal(self) -> bool:
        return self.kind in TERMINAL_STAGES


class ImageJobState(WorkerModel):
    job_id: str
    status: ImageJobStatus
    priority: ImagePriority
    width: int
    height: int
    steps: int
    seed: int
    position: int | None = None
    last_event: ImageProgress | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class WorkerHealth(WorkerModel):
    status: str
    backend: str
    model_id: str
    loaded: bool
    loading: bool
    queue_length: int
    running_job_id: str | None = None
    idle_unload_seconds: float


@dataclass(frozen=True)
class GeneratedImage:
    job_id: str
    png: bytes
    width: int
    height: int
    steps: int
    seed: int
