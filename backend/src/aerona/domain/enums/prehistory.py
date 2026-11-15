from enum import StrEnum


class PrehistoryKind(StrEnum):
    FULL = "full"
    LIVING = "living"
    SOULS = "souls"
    DREAMT = "dreamt"
    MIRRORED = "mirrored"
    PALACE = "palace"
    VOYAGE = "voyage"
    PHENOMENON = "phenomenon"
    CORPSE = "corpse"


class PrehistoryState(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    DONE = "done"
    ABORTED = "aborted"


class PrehistorySource(StrEnum):
    SIMULATED = "simulated"
    BACKFILLED = "backfilled"
    MIRRORED = "mirrored"
    DREAMT = "dreamt"
    DERIVED = "derived"


class DeepTimeState(StrEnum):
    RUNNING = "running"
    DONE = "done"
    STOPPED = "stopped"
