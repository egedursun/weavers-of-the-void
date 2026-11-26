import asyncio
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from aerona.llm.content import ImagePart
from aerona.llm.events import EventSink
from aerona.llm.tools import AgentTool


class StopReason(StrEnum):
    COMPLETED = "completed"
    STEP_LIMIT = "step_limit"
    STOPPED = "stopped"
    REFUSED = "refused"


@dataclass(frozen=True)
class RunRequest:
    system: str
    prompt: str
    tools: tuple[AgentTool, ...]
    model: str
    max_turns: int
    images: tuple[ImagePart, ...] = ()


@dataclass(frozen=True)
class RunEnd:
    stop: StopReason
    turns: int


class ModelBackend(Protocol):
    async def run(self, request: RunRequest, events: EventSink, stop: asyncio.Event) -> RunEnd: ...

    async def models(self) -> list[str]: ...

    async def close(self) -> None: ...
