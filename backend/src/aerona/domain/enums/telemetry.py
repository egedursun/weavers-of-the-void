from enum import StrEnum


class LlmCallKind(StrEnum):
    AGENT = "agent"
    STRUCTURED = "structured"


class LlmCallStatus(StrEnum):
    OK = "ok"
    PARTIAL = "partial"
    ERROR = "error"


class UsageSort(StrEnum):
    TIME = "time"
    TOTAL_TOKENS = "total_tokens"
    INPUT_TOKENS = "input_tokens"
    OUTPUT_TOKENS = "output_tokens"
    DURATION = "duration"
    EPOCH = "epoch"
    MODEL = "model"
    STEP = "step"


class UsageBucket(StrEnum):
    EPOCH = "epoch"
    HOUR = "hour"
    DAY = "day"
