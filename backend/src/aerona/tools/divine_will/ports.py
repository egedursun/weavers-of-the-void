from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, cast

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.rules.model import RuleDescriptor
from aerona.rules.registry import Rules
from aerona.tools.divine_will.framework import WillCall


@dataclass(frozen=True)
class SectionView:
    title: str
    facts: tuple[tuple[str, str], ...] = ()
    lines: tuple[str, ...] = ()


@dataclass(frozen=True)
class LinkView:
    source: int
    target: int
    kind: str
    forward: bool
    description: str | None = None


@dataclass(frozen=True)
class PathView:
    found: bool
    path: tuple[int, ...] = ()
    names: Mapping[int, str] = field(default_factory=dict)
    steps: tuple[LinkView, ...] = ()


@dataclass(frozen=True)
class ActionCard:
    id: str
    title: str
    group: str
    is_job: bool
    cost: str
    confirmation: str | None
    input_model: type[BaseModel]
    accepts: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def schema(self) -> dict[str, Any]:
        return self.input_model.model_json_schema()


class WillReads(Protocol):
    async def typed_sections(self, session: AsyncSession, names: Mapping[int, str], node_id: int) -> list[SectionView]: ...

    async def links(self, session: AsyncSession, node_id: int) -> list[LinkView]: ...

    async def path(self, session: AsyncSession, first: int, second: int, depth: int) -> PathView: ...


class ActionDesk(Protocol):
    def cards(self, rules: Rules) -> Sequence[ActionCard]: ...


class ReadHost(Protocol):
    @property
    def lore_reads(self) -> WillReads: ...

    @property
    def action_desk(self) -> ActionDesk: ...


def will_reads(call: WillCall) -> WillReads:
    return cast(ReadHost, call.services).lore_reads


def action_desk(call: WillCall) -> ActionDesk:
    return cast(ReadHost, call.services).action_desk


class RuleDeskPort(Protocol):
    def find(self, namespace: str, key: str) -> RuleDescriptor | None: ...

    async def change(self, namespace: str, key: str, value: float | None) -> RuleDescriptor: ...
