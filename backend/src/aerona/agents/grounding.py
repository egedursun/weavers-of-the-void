from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.ports import LanguageModel
from aerona.catalog.genesis import TECHNOLOGY_LABELS
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.db.tables.technology import TECH_LEVEL_MAX, TechnologyProfileRow
from aerona.domain.enums.providers import ModelRole
from aerona.llm.content import AgentWatch, ImagePart, ModelCapabilities
from aerona.llm.records import AgentRun
from aerona.llm.tools import AgentTool

GROUND_HEAD = "WHAT THE PLAYER SET FOR THIS WORLD (everything you write follows it):"


async def setting_line(session: AsyncSession) -> str:
    cosmos = await CosmosRepository(session).get()
    settings = cosmos.genesis_settings if cosmos is not None else None
    parts: list[str] = []
    if settings is not None:
        parts.append(f"it began in the {TECHNOLOGY_LABELS[settings.technology].lower()}")
        parts.append(f"magic {settings.magic} of {PERCENT}")
        parts.append(f"danger {settings.danger} of {PERCENT}")
    world_id = cosmos.primary_world_id if cosmos is not None else None
    if world_id is not None:
        rows = await session.scalars(select(TechnologyProfileRow).where(TechnologyProfileRow.holder_node_id == world_id).order_by(TechnologyProfileRow.family))
        levels = [f"{spoken(row.family)} {row.level}" for row in rows]
        if levels:
            parts.append(f"its technology now, from 0 to {TECH_LEVEL_MAX}: " + ", ".join(levels))
    return "; ".join(parts)


async def world_ground(session: AsyncSession) -> str:
    cosmos = await CosmosRepository(session).get()
    if cosmos is None:
        return ""
    lines = [GROUND_HEAD]
    if cosmos.seed_idea:
        lines.append(f"SEED: {cosmos.seed_idea}")
    setting = await setting_line(session)
    if setting:
        lines.append(f"SETTING: {setting}")
    if cosmos.tone:
        lines.append(f"TONE: {cosmos.tone}")
    return "\n".join(lines) if len(lines) > 1 else ""


def grounded(ground: str, system_prompt: str) -> str:
    return f"{ground}\n\n{system_prompt}" if ground else system_prompt


class GroundedModel:
    def __init__(self, inner: LanguageModel, database: Database) -> None:
        self.inner = inner
        self.database = database

    @property
    def enabled(self) -> bool:
        return self.inner.enabled

    def ready(self, role: ModelRole) -> bool:
        return self.inner.ready(role)

    def model_of(self, role: ModelRole) -> str:
        return self.inner.model_of(role)

    async def ground(self) -> str:
        async with self.database.read() as session:
            return await world_ground(session)

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
        role: ModelRole = ModelRole.WRITING,
    ) -> T:
        return await self.inner.structured(
            label,
            grounded(await self.ground(), system_prompt),
            prompt,
            output=output,
            attempts=attempts,
            schema=schema,
            timeout_seconds=timeout_seconds,
            role=role,
        )

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
        return await self.inner.run_agent(
            label,
            grounded(await self.ground(), system_prompt),
            prompt,
            tools=tools,
            max_turns=max_turns,
            timeout_seconds=timeout_seconds,
            images=images,
            watch=watch,
            role=role,
        )

    async def capabilities(self, role: ModelRole = ModelRole.CONVERSATION) -> ModelCapabilities:
        return await self.inner.capabilities(role)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)
