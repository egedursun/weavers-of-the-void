import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from aerona.domain.enums.providers import ModelRole
from aerona.llm.backends.base import StopReason
from aerona.llm.content import AgentWatch, ImagePart
from aerona.llm.events import ReplyEnded, RunEvent, ToolCalled, ToolFinished
from aerona.llm.records import AgentRun, Usage
from aerona.llm.tools import AgentTool
from tests.agents.fakes import FakeModel


@dataclass(frozen=True)
class Say:
    text: str


@dataclass(frozen=True)
class Think:
    text: str


@dataclass(frozen=True)
class Use:
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Break:
    error: Exception


@dataclass(frozen=True)
class Hang:
    started: asyncio.Event


Step = Say | Think | Use | Break | Hang


@dataclass
class Seen:
    system: str
    prompt: str
    tools: list[str]
    images: list[ImagePart]
    max_turns: int | None


@dataclass
class ToolOutcome:
    tool: str
    text: str
    is_error: bool


@dataclass
class ScriptedWill(FakeModel):
    turns: list[list[Step]] = field(default_factory=list)
    seen: list[Seen] = field(default_factory=list)
    outcomes: list[ToolOutcome] = field(default_factory=list)

    def plan(self, *turns: Sequence[Step]) -> None:
        self.turns.extend(list(turn) for turn in turns)

    async def run_agent(
        self,
        label: str,
        system_prompt: str,
        prompt: str,
        *,
        tools: Sequence[AgentTool],
        max_turns: int | None = None,
        timeout_seconds: int | None = None,
        images: Sequence[ImagePart] = (),
        watch: AgentWatch | None = None,
        role: ModelRole = ModelRole.WORLD_AGENTS,
    ) -> AgentRun:
        self.seen.append(Seen(system_prompt, prompt, [tool.name for tool in tools], list(images), max_turns))
        script = self.turns.pop(0) if self.turns else [Say("Done.")]
        offered = {tool.name: tool for tool in tools}
        texts: list[str] = []
        replies = 0
        for index, step in enumerate(script):
            if isinstance(step, Break):
                raise step.error
            if isinstance(step, Hang):
                step.started.set()
                await asyncio.Event().wait()
            replies += 1
            if isinstance(step, Say):
                texts.append(step.text)
                await self.show(watch, ReplyEnded(step.text, ""))
            elif isinstance(step, Think):
                await self.show(watch, ReplyEnded("", step.text))
            elif isinstance(step, Use):
                call_id = f"call-{len(self.seen)}-{index}"
                await self.show(watch, ReplyEnded("", ""))
                await self.show(watch, ToolCalled(call_id, step.tool, dict(step.arguments)))
                answer = await offered[step.tool].handler(dict(step.arguments))
                self.outcomes.append(ToolOutcome(step.tool, answer.text, answer.is_error))
                await self.show(watch, ToolFinished(call_id, step.tool, answer.text, answer.is_error))
            if watch is not None and watch.stopped:
                return AgentRun(text="\n".join(texts), usage=Usage(turns=replies), completed=False, stop_reason=StopReason.STOPPED.value)
        return AgentRun(
            text="\n".join(texts), usage=Usage(input_tokens=10, output_tokens=5, turns=replies), completed=True, stop_reason=StopReason.COMPLETED.value
        )

    @staticmethod
    async def show(watch: AgentWatch | None, event: RunEvent) -> None:
        if watch is not None:
            await watch.seen(event)
