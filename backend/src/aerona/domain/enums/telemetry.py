from enum import StrEnum


class LlmCallKind(StrEnum):
    AGENT = "agent"
    STRUCTURED = "structured"


class LlmCallStatus(StrEnum):
    OK = "ok"
    PARTIAL = "partial"
    ERROR = "error"
