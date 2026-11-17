from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from aerona.llm.token_count import TokenMeter


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

    def count(self, meter: TokenMeter) -> None:
        self.input_tokens += meter.input_tokens
        self.output_tokens += meter.output_tokens

    def absorb(self, cost: float | None, turns: int | None) -> None:
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
