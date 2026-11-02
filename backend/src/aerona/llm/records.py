from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class CallKind(StrEnum):
    STRUCTURED = "structured"
    AGENT = "agent"


class CallOutcome(StrEnum):
    OK = "ok"
    FAILED = "failed"
    TIMEOUT = "timeout"
    DISABLED = "disabled"


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    turns: int = 0
    completed: bool = True

    def absorb(self, usage: dict[str, Any] | None, cost: float | None, turns: int | None) -> None:
        data = usage or {}
        self.input_tokens += int(data.get("input_tokens", 0)) + int(data.get("cache_read_input_tokens", 0)) + int(data.get("cache_creation_input_tokens", 0))
        self.output_tokens += int(data.get("output_tokens", 0))
        self.cost_usd += float(cost or 0.0)
        self.turns += int(turns or 0)


@dataclass
class CallRecord:
    label: str
    kind: CallKind
    model: str
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    duration_seconds: float = 0.0
    attempts: int = 0
    outcome: CallOutcome = CallOutcome.OK
    error: str | None = None
    usage: Usage = field(default_factory=Usage)


@dataclass
class AgentRun:
    text: str
    usage: Usage
    completed: bool
    stop_reason: str | None

    def __post_init__(self) -> None:
        self.usage.completed = self.completed
