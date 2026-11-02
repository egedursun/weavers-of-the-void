from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from aerona.catalog.gates import GATE_RULES, Gate
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, PendingJobKind
from aerona.domain.enums.rarity import Rarity
from aerona.prompts.tools.ids import MortalToolId, SonToolId
from aerona.rules.registry import Rules
from aerona.tools.framework.inputs import ToolInput

RuleNumber = Callable[[Rules], int]


def son_standard_action(rules: Rules) -> int:
    return rules.son_tools.standard_action_cost


def mortal_standard_action(rules: Rules) -> int:
    return rules.mortal_tools.standard_action_cost


def no_cost(_rules: Rules) -> int:
    return 0


def gate(key: Gate) -> Callable[[Rules], Rarity]:
    def minimum(rules: Rules) -> Rarity:
        return Rarity.from_rank(GATE_RULES[key](rules))

    return minimum


@dataclass(frozen=True)
class ToolMeta:
    action_kind: ActionKind
    action_cost: RuleNumber
    essence_cost: RuleNumber = no_cost
    rarity_gate: Callable[[Rules], Rarity] | None = None
    read_only: bool = False
    flexible_actions: bool = False
    long_job: PendingJobKind | None = None

    @property
    def free(self) -> bool:
        return self.read_only

    def actions(self, rules: Rules) -> int:
        return 0 if self.read_only else self.action_cost(rules)

    def essence(self, rules: Rules) -> int:
        return self.essence_cost(rules)

    def minimum_rarity(self, rules: Rules) -> Rarity | None:
        return self.rarity_gate(rules) if self.rarity_gate is not None else None


@dataclass(frozen=True)
class LongJob[CallT, JobResultT]:
    kind: PendingJobKind
    essence: int
    action_points: int
    label: str
    run: Callable[[], Awaitable[JobResultT]]
    finish: Callable[[CallT, JobResultT], Awaitable[str]]
    trace_key: Callable[[JobResultT], str]


ToolOutcome = str | LongJob[Any, Any]


@dataclass(frozen=True)
class ToolSpec[CallT, InputT: ToolInput]:
    tool_id: SonToolId | MortalToolId
    agent: AgentKind
    input_model: type[InputT]
    meta: ToolMeta
    handler: Callable[[CallT, InputT], Awaitable[ToolOutcome]]
    tags: frozenset[str] = field(default_factory=frozenset)

    @property
    def name(self) -> str:
        return self.tool_id.value
