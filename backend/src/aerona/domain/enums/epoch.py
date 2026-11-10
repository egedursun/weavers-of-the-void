from enum import IntEnum, StrEnum


class EpochPhase(IntEnum):
    NOT_STARTED = 0
    GODS = 1
    MORTALS = 2
    ENGINE = 3
    FATE = 4
    TRANSITION = 5


class EpochStepKind(StrEnum):
    COMPLETION = "completion"
    BACKUP = "backup"
    DISTRIBUTION = "distribution"
    NAMING = "naming"
    FATE_JUDGMENT = "fate_judgment"
    CHRONICLE = "chronicle"
    VOICES = "voices"
    COUNCIL = "council"
    EPOCH_WORDS = "epoch_words"
    LOCAL_GODS = "local_gods"
    TRANSITION = "transition"
    WORLD_BIRTH = "world_birth"
    NETWORK_REPAIR = "network_repair"
    PRUNE = "prune"
    IMAGES = "images"
    LOCALISATION = "localisation"
    BACKGROUND = "background"


class EpochStepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class DeferredStepKind(StrEnum):
    WORLD_BIRTH = "world_birth"
    COUNCIL = "council"
    SENSED_WORLD = "sensed_world"


class DeferredStepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    HELD = "held"


class EngineStage(StrEnum):
    TICK = "tick"
    TRANSITION = "transition"
    AFTER_TRANSITION = "after_transition"
