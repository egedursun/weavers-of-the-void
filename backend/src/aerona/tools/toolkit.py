from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from claude_agent_sdk import SdkMcpTool
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.world import LoreLanguage
from aerona.engine.context import Publisher
from aerona.prompts import tool_text
from aerona.prompts.tools.ids import MortalToolId, SonToolId
from aerona.prompts.tools.text import RenderedToolText
from aerona.rules.registry import Rules
from aerona.tools.framework.actors import MortalToolRuntime, SonToolRuntime
from aerona.tools.framework.ports import ToolPorts
from aerona.tools.framework.runtime import DoneAction, RuntimeSettings, ToolCatalogue, ToolRuntime, catalogue_of, silent_publisher
from aerona.tools.framework.sdk import sdk_tool
from aerona.tools.framework.spec import ToolSpec
from aerona.tools.framework.turn import start_turn
from aerona.tools.mortal.registry import mortal_may_use, mortal_specs, mortal_state, mortal_text_context
from aerona.tools.son.availability import world_state
from aerona.tools.son.registry import son_may_use, son_specs, son_text_context


class TurnToolkit:
    def __init__(self, runtime: ToolRuntime[Any], texts: dict[str, RenderedToolText]) -> None:
        self.runtime = runtime
        self._texts = texts

    @property
    def catalogue(self) -> ToolCatalogue:
        return self.runtime.catalogue

    @property
    def done(self) -> Sequence[DoneAction]:
        return self.runtime.done

    @property
    def created_entity_ids(self) -> Sequence[int]:
        return self.runtime.created_entity_ids

    @property
    def read_only_tools(self) -> frozenset[str]:
        return frozenset(spec.name for spec in self.runtime.specs if spec.meta.read_only)

    def tools(self) -> list[SdkMcpTool[Any]]:
        return [sdk_tool(self.runtime, spec, self._texts[spec.name]) for spec in self.runtime.specs]

    async def settle_long_jobs(self) -> None:
        await self.runtime.settle_long_jobs()


@dataclass(frozen=True)
class WorldSettings:
    rules: Rules
    seed: int
    language: LoreLanguage


class Toolkits:
    def __init__(self, database: Database, ports: ToolPorts | None = None, publish: Publisher = silent_publisher, rules: Rules | None = None) -> None:
        self._database = database
        self._ports = ports or ToolPorts()
        self._publish = publish
        self._rules = rules

    async def _world(self, session: AsyncSession) -> WorldSettings:
        cosmos = await CosmosRepository(session).require_cosmos()
        rules = self._rules or rules_from_snapshot(cosmos.rules_snapshot)
        return WorldSettings(rules, cosmos.rng_seed, cosmos.lore_language)

    async def son_specs_for(self, session: AsyncSession, son: SonRow) -> list[ToolSpec[Any, Any]]:
        world = await self._world(session)
        state = await world_state(session, son)
        return [spec for spec in son_specs() if son_may_use(spec, son, world.rules, state, self._ports)]

    async def mortal_specs_for(self, session: AsyncSession, mortal: EntityRow) -> list[ToolSpec[Any, Any]]:
        world = await self._world(session)
        state = await mortal_state(session, world.rules, mortal)
        return [spec for spec in mortal_specs() if mortal_may_use(spec, mortal, world.rules, state, self._ports)]

    async def son_catalogue(self, session: AsyncSession, son: SonRow) -> ToolCatalogue:
        world = await self._world(session)
        return catalogue_of(await self.son_specs_for(session, son), world.rules)

    async def son_toolkit(self, son_id: int, epoch: int, action_points: int) -> TurnToolkit:
        async with self._database.write() as session:
            world = await self._world(session)
            son = await session.get(SonRow, son_id)
            if son is None:
                raise NotFoundError("No such son.")
            await start_turn(session, son_id, AgentKind.SON, epoch, action_points)
            specs = await self.son_specs_for(session, son)
            texts = {spec.name: tool_text(SonToolId(spec.name), world.rules, await son_text_context(session, world.rules, son, spec)) for spec in specs}
        settings = RuntimeSettings(world.rules, epoch, world.seed, world.language, son_id, self._publish)
        return TurnToolkit(SonToolRuntime(self._database, settings, specs, self._ports), texts)

    async def mortal_toolkit(self, entity_id: int, epoch: int, action_points: int) -> TurnToolkit:
        async with self._database.write() as session:
            world = await self._world(session)
            mortal = await session.get(EntityRow, entity_id)
            if mortal is None:
                raise NotFoundError("No such mortal.")
            await start_turn(session, entity_id, AgentKind.MORTAL, epoch, action_points)
            specs = await self.mortal_specs_for(session, mortal)
            texts = {spec.name: tool_text(MortalToolId(spec.name), world.rules, mortal_text_context(spec)) for spec in specs}
        settings = RuntimeSettings(world.rules, epoch, world.seed, world.language, entity_id, self._publish)
        return TurnToolkit(MortalToolRuntime(self._database, settings, specs, self._ports), texts)
