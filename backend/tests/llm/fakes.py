import asyncio
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from aerona.domain.enums.providers import ModelRole
from aerona.llm.backends.base import ModelBackend, RunEnd, RunRequest, StopReason
from aerona.llm.events import EventSink, ReplyEnded, TextDelta, ToolPreparing
from aerona.llm.routes import ModelRoute
from aerona.rules.registry import Rules
from aerona.rules.registry.model import ModelRules


class FixedRules:
    def __init__(self) -> None:
        self.current = Rules(model=ModelRules(retry_wait_1=0, retry_wait_2=0, retry_wait_3=0))


@dataclass(frozen=True)
class Speak:
    text: str


@dataclass(frozen=True)
class Call:
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Hang:
    pass


Move = Speak | Call | Hang | Exception


@dataclass
class FakeBackend:
    runs: list[list[Move]] = field(default_factory=list)
    requests: list[RunRequest] = field(default_factory=list)
    replies: list[str] = field(default_factory=list)

    async def run(self, request: RunRequest, events: EventSink, stop: asyncio.Event) -> RunEnd:
        self.requests.append(request)
        moves = self.runs.pop(0) if self.runs else [Speak("done")]
        tools = {tool.name: tool for tool in request.tools}
        turns = 0
        for number, move in enumerate(moves):
            if isinstance(move, Exception):
                raise move
            if isinstance(move, Hang):
                await asyncio.Event().wait()
            turns += 1
            if isinstance(move, Speak):
                events(TextDelta(move.text))
                events(ReplyEnded(move.text, ""))
            elif isinstance(move, Call):
                events(ToolPreparing(f"p{number}", move.tool))
                events(ReplyEnded("", ""))
                reply = await tools[move.tool].handler(dict(move.arguments))
                self.replies.append(reply.text)
            if stop.is_set():
                return RunEnd(StopReason.STOPPED, turns)
        return RunEnd(StopReason.COMPLETED, turns)

    async def models(self) -> list[str]:
        return ["fake-model"]

    async def close(self) -> None:
        return None


def route(backend: ModelBackend, provider: str = "Test", model: str = "fake-model", sees_images: bool | None = True) -> ModelRoute:
    async def open_backend() -> ModelBackend:
        return backend

    return ModelRoute(provider, model, sees_images, open_backend)


@dataclass
class FakeRoutes:
    chains: dict[ModelRole, list[ModelRoute]] = field(default_factory=dict)

    def routes(self, role: ModelRole) -> Sequence[ModelRoute]:
        return self.chains.get(role, [])


def every_role(*routes: ModelRoute) -> FakeRoutes:
    return FakeRoutes({role: list(routes) for role in ModelRole})


def answered(value: dict[str, Any]) -> list[Move]:
    return [Call("answer", value)]


def as_json(value: dict[str, Any]) -> str:
    return json.dumps(value)
