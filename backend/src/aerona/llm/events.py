from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TextDelta:
    text: str


@dataclass(frozen=True)
class ThoughtDelta:
    text: str


@dataclass(frozen=True)
class ToolPreparing:
    call_id: str
    tool: str


@dataclass(frozen=True)
class ToolWriting:
    call_id: str
    tool: str
    chars: int


@dataclass(frozen=True)
class ToolCalled:
    call_id: str
    tool: str
    input: dict[str, Any]


@dataclass(frozen=True)
class ToolFinished:
    call_id: str
    tool: str
    text: str
    is_error: bool


@dataclass(frozen=True)
class ReplyEnded:
    text: str
    thoughts: str


RunEvent = TextDelta | ThoughtDelta | ToolPreparing | ToolWriting | ToolCalled | ToolFinished | ReplyEnded
EventSink = Callable[[RunEvent], None]
