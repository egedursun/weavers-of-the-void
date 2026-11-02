from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.world import WorldType
from aerona.prompts.contexts.blocks import SummarySection
from aerona.rules.registry import Rules


class ReadViews(Protocol):
    async def world_summary(self, session: AsyncSession, rules: Rules, son: SonRow, section: SummarySection | None) -> str: ...

    async def son_memory(self, session: AsyncSession, rules: Rules, son: SonRow) -> str: ...

    async def mortal_view(self, session: AsyncSession, rules: Rules, mortal: EntityRow) -> str: ...


@dataclass(frozen=True)
class BornChild:
    son_id: int
    name: str
    title: str
    rarity_label: str


class ChildBirth(Protocol):
    async def birth_child(self, parent_son_id: int, inspiration: str, co_parent_son_id: int | None) -> BornChild: ...


@dataclass(frozen=True)
class WorldBirthOrder:
    son_id: int
    inspiration: str
    world_type: WorldType | None
    star_id: int | None
    parent_world_id: int | None
    new_star: bool


@dataclass(frozen=True)
class BornWorld:
    world_id: int
    name: str
    type_label: str


class WorldBirth(Protocol):
    async def birth_world(self, order: WorldBirthOrder) -> BornWorld: ...


@dataclass(frozen=True)
class ToolPorts:
    views: ReadViews | None = None
    child_birth: ChildBirth | None = None
    world_birth: WorldBirth | None = None
