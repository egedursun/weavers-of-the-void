from enum import StrEnum

from aerona.domain.enums.agent import AgentKind, PendingJobKind
from aerona.prompts.contexts.base import PromptContext


class ToolRejectionContext(PromptContext):
    reason: str


class ToolFailureContext(PromptContext):
    error: str


class SonGateContext(PromptContext):
    name: str
    state_label: str
    sleep_left: int | None = None


class MortalGateContext(PromptContext):
    name: str
    status_label: str


class CaptiveGateContext(PromptContext):
    captor: str


class ActionsSpentContext(PromptContext):
    agent: AgentKind
    remaining: int = 0


class StatusLineContext(PromptContext):
    remaining: int
    essence: int
    max_essence: int


class SleepNoticeContext(PromptContext):
    asleep: bool
    state_label: str


class PendingLongJobContext(PromptContext):
    job: PendingJobKind | None = None


class EntityStateKind(StrEnum):
    UNSELECTED = "unselected"
    MISSING = "missing"
    DEAD = "dead"
    DESTROYED = "destroyed"
    REJECTED = "rejected"
    FULFILLED = "fulfilled"
    OTHER = "other"


class EntityStateContext(PromptContext):
    kind: EntityStateKind
    id: int = 0
    name: str = ""
    age: int | None = None
    state_label: str = ""


class FieldErrorKind(StrEnum):
    MISSING = "missing"
    TOO_SMALL = "too_small"
    TOO_BIG = "too_big"
    NOT_INTEGER = "not_integer"
    NOT_NUMBER = "not_number"


class FieldErrorContext(PromptContext):
    kind: FieldErrorKind
    field: str
    limit: float | None = None
    given: str = ""


class PerEpochLimitContext(PromptContext):
    rule_path: str
    value: int
