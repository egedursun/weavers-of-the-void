from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class JobKind(StrEnum):
    EPOCH = "epoch"
    GENESIS = "genesis"
    DEEPEN = "deepen"
    SUMMON = "summon"
    IMAGE = "image"
    BACKUP = "backup"
    BOOK = "book"
    IMPORT = "import"
    SIMULATION = "simulation"
    SON_TURN = "son_turn"
    NAMING = "naming"
    COMPLETION = "completion"
    REVELATION = "revelation"
    WORLD_CREATION = "world_creation"
    AWAKENING = "awakening"
    CONTENT = "content"
    MAINTENANCE = "maintenance"
    RETRY = "retry"


TERMINAL_JOB_STATUSES = frozenset({JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.INTERRUPTED})
