from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import SdkMcpTool
from pydantic import BaseModel

from aerona.agents.turns.ports import DoneAction, ToolCatalogue
from aerona.llm.errors import LlmDisabledError
from aerona.llm.records import AgentRun, Usage

Responder = Callable[[str], BaseModel]


@dataclass
class Call:
    label: str
    system: str
    prompt: str
    schema: dict[str, Any] | None


@dataclass
class FakeModel:
    enabled: bool = True
    scripted: dict[type[BaseModel], list[BaseModel | Exception | Responder]] = field(default_factory=lambda: defaultdict(list))
    runs: list[AgentRun | Exception | Callable[[], AgentRun]] = field(default_factory=list)
    fallback: dict[type[BaseModel], Responder] = field(default_factory=dict)
    default_run: AgentRun | None = None
    calls: list[Call] = field(default_factory=list)

    def script(self, output: type[BaseModel], *responses: BaseModel | Exception | Responder) -> None:
        self.scripted[output].extend(responses)

    def labels(self) -> list[str]:
        return [call.label for call in self.calls]

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
    ) -> T:
        if not self.enabled:
            raise LlmDisabledError("LLM calls are disabled.")
        self.calls.append(Call(label, system_prompt, prompt, schema))
        queue = self.scripted[output]
        if not queue and output in self.fallback:
            return output.model_validate(self.fallback[output](prompt).model_dump())
        if not queue:
            raise LookupError(f"No scripted {output.__name__} for {label}.")
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        value = item(prompt) if callable(item) and not isinstance(item, BaseModel) else item
        return output.model_validate(value.model_dump())

    async def run_agent(
        self,
        label: str,
        system_prompt: str,
        prompt: str,
        *,
        tools: list[SdkMcpTool[Any]],
        max_turns: int | None = None,
        timeout_seconds: int | None = None,
    ) -> AgentRun:
        if not self.enabled:
            raise LlmDisabledError("LLM calls are disabled.")
        self.calls.append(Call(label, system_prompt, prompt, None))
        if not self.runs and self.default_run is not None:
            return self.default_run
        item = self.runs.pop(0)
        if isinstance(item, Exception):
            raise item
        return item() if callable(item) else item


def spoken(text: str, completed: bool = True, stop_reason: str | None = "success") -> AgentRun:
    return AgentRun(text=text, usage=Usage(), completed=completed, stop_reason=stop_reason)


@dataclass
class ScriptedToolkit:
    actions: list[DoneAction] = field(default_factory=list)
    created: list[int] = field(default_factory=list)
    listing: ToolCatalogue = field(default_factory=lambda: ToolCatalogue(names=["create_people"], paid=["create_people"], free=[]))

    @property
    def catalogue(self) -> ToolCatalogue:
        return self.listing

    @property
    def done(self) -> Sequence[DoneAction]:
        return self.actions

    @property
    def created_entity_ids(self) -> Sequence[int]:
        return self.created

    @property
    def read_only_tools(self) -> frozenset[str]:
        return frozenset()

    def tools(self) -> list[SdkMcpTool[Any]]:
        return []

    async def settle_long_jobs(self) -> None:
        return None


@dataclass
class ScriptedToolkits:
    son: ScriptedToolkit = field(default_factory=ScriptedToolkit)
    mortal: ScriptedToolkit = field(default_factory=ScriptedToolkit)
    requests: list[tuple[str, int, int]] = field(default_factory=list)

    async def son_toolkit(self, son_id: int, epoch: int, action_points: int) -> ScriptedToolkit:
        self.requests.append(("son", son_id, action_points))
        return self.son

    async def mortal_toolkit(self, entity_id: int, epoch: int, action_points: int) -> ScriptedToolkit:
        self.requests.append(("mortal", entity_id, action_points))
        return self.mortal
