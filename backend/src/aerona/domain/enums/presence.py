from enum import StrEnum


class PresenceGuise(StrEnum):
    CREATOR = "creator"
    UNNAMED_POWER = "unnamed_power"
    DREAM_VOICE = "dream_voice"
    ORDINARY = "ordinary"


class PresenceRecord(StrEnum):
    ON_RECORD = "on_record"
    OFF_RECORD = "off_record"


class PresenceStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class PresenceExchangeStatus(StrEnum):
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PresenceEventKind(StrEnum):
    TEXT = "text"
    THOUGHT = "thought"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    RETRY = "retry"


class SpeakerGroup(StrEnum):
    SONS = "sons"
    FOREIGN_GODS = "foreign_gods"
    MORTALS = "mortals"
    SPIRITS = "spirits"
    BEINGS = "beings"
    BEASTS = "beasts"
