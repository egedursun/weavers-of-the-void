from enum import StrEnum


class BackendName(StrEnum):
    MLX = "mlx"
    DIFFUSERS = "diffusers"
    FAKE = "fake"


class Isolation(StrEnum):
    PROCESS = "process"
    INLINE = "inline"


class JobPriority(StrEnum):
    MANUAL = "manual"
    BULK = "bulk"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


class EventKind(StrEnum):
    QUEUED = "queued"
    LOADING = "loading"
    ENCODING = "encoding"
    STEP = "step"
    DECODING = "decoding"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


TERMINAL_STATUSES = frozenset({JobStatus.DONE, JobStatus.ERROR, JobStatus.CANCELLED})
TERMINAL_EVENTS = frozenset({EventKind.DONE, EventKind.ERROR, EventKind.CANCELLED})
PRIORITY_RANK = {JobPriority.MANUAL: 0, JobPriority.BULK: 1}
