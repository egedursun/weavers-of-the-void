from enum import StrEnum


class LibraryJobKind(StrEnum):
    EXPORT = "export"
    IMPORT = "import"


class LibraryJobStatus(StrEnum):
    RUNNING = "running"
    WAITING = "waiting"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LibraryJobStage(StrEnum):
    SNAPSHOT = "snapshot"
    GATHER = "gather"
    PACK = "pack"
    CHECK = "check"
    PLACE = "place"
    REGISTER = "register"


class LibraryStreamKind(StrEnum):
    HELLO = "hello"
    UNIVERSE = "universe"
    REMOVED = "removed"
    TRASH = "trash"
    JOB = "job"
