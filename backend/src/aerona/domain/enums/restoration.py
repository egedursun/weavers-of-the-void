from enum import StrEnum


class RestorationBasis(StrEnum):
    BLOODLINE = "bloodline"
    FAITH = "faith"
    LAW = "law"
    MEMORY = "memory"
    FOREIGN_BACKING = "foreign_backing"


class RestorationStage(StrEnum):
    MEMORY = "memory"
    MOVEMENT = "movement"
    RISING = "rising"
    RESTORED = "restored"
    FAILED = "failed"


OPEN_STAGES = frozenset({RestorationStage.MEMORY, RestorationStage.MOVEMENT, RestorationStage.RISING})


class RestorationFailure(StrEnum):
    MEMORY_FADED = "memory_faded"
    PUT_DOWN = "put_down"
    NO_LANDS = "no_lands"
