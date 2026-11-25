from collections.abc import Callable, Sequence
from typing import Any, Protocol

from claude_agent_sdk import SdkMcpTool
from pydantic import BaseModel

from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.llm.content import AgentWatch, ImagePart, ModelCapabilities
from aerona.llm.records import AgentRun

Publish = Callable[[EventKind, dict[str, Any]], None]


def silent(kind: EventKind, payload: dict[str, Any]) -> None:
    del kind, payload


class LanguageModel(Protocol):
    @property
    def enabled(self) -> bool: ...

    async def structured[T: BaseModel](
        self,
        label: str,
        system_prompt: str,
        prompt: str,
        *,
        output: type[T],
        attempts: int | None = None,
        schema: dict[str, Any] | None = None,
        timeout_seconds: int | None = None,
    ) -> T: ...

    async def run_agent(
        self,
        label: str,
        system_prompt: str,
        prompt: str,
        *,
        tools: list[SdkMcpTool[Any]],
        max_turns: int | None = None,
        timeout_seconds: int | None = None,
        images: Sequence[ImagePart] = (),
        watch: AgentWatch | None = None,
    ) -> AgentRun: ...

    async def capabilities(self) -> ModelCapabilities: ...


def bus_publisher(bus: EventBus) -> Publish:
    def publish(kind: EventKind, payload: dict[str, Any]) -> None:
        bus.publish(kind, payload)

    return publish
