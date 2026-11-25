import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import AssistantMessage, SdkMcpTool, TextBlock, ThinkingBlock, ToolResultBlock, ToolUseBlock, UserMessage

from aerona.constants.llm import HAIKU_MODEL_ID, TOOL_NAME_PREFIX
from aerona.llm.content import AgentWatch, ImagePart
from aerona.llm.records import AgentRun, Usage
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
        tools: list[SdkMcpTool[Any]],
        max_turns: int | None = None,
        timeout_seconds: int | None = None,
        images: Sequence[ImagePart] = (),
        watch: AgentWatch | None = None,
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
                await self.show(watch, AssistantMessage(content=[TextBlock(step.text)], model=HAIKU_MODEL_ID))
            elif isinstance(step, Think):
                await self.show(watch, AssistantMessage(content=[ThinkingBlock(step.text, "signature")], model=HAIKU_MODEL_ID))
            elif isinstance(step, Use):
                call_id = f"call-{len(self.seen)}-{index}"
                await self.show(
                    watch, AssistantMessage(content=[ToolUseBlock(call_id, f"{TOOL_NAME_PREFIX}{step.tool}", step.arguments)], model=HAIKU_MODEL_ID)
                )
                answer = await offered[step.tool].handler(dict(step.arguments))
                text = "\n".join(str(part.get("text", "")) for part in answer["content"])
                self.outcomes.append(ToolOutcome(step.tool, text, bool(answer.get("is_error"))))
                await self.show(watch, UserMessage(content=[ToolResultBlock(call_id, answer["content"], bool(answer.get("is_error")))]))
            if watch is not None and watch.stopped:
                return AgentRun(text="\n".join(texts), usage=Usage(turns=replies), completed=False, stop_reason="paused")
        return AgentRun(text="\n".join(texts), usage=Usage(input_tokens=10, output_tokens=5, turns=replies), completed=True, stop_reason="success")

    @staticmethod
    async def show(watch: AgentWatch | None, message: object) -> None:
        if watch is not None:
            await watch.seen(message)
