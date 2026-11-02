from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.mortal import mortal_context
from aerona.agents.context.scope import load_scope
from aerona.agents.context.son_memory import son_memory
from aerona.agents.context.world_summary import world_summary
from aerona.agents.runtime import AgentRuntime
from aerona.agents.summoner import birth_child
from aerona.agents.world_birth import BirthPlan, birth_world
from aerona.catalog.rarities import RARITY_LABELS
from aerona.catalog.worlds import WORLD_TYPES
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import SummarySection
from aerona.rules.registry import Rules
from aerona.tools.framework.ports import BornChild, BornWorld, ToolPorts, WorldBirthOrder
from aerona.tools.toolkit import Toolkits


class AgentReadViews:
    async def world_summary(self, session: AsyncSession, rules: Rules, son: SonRow, section: SummarySection | None) -> str:
        return await world_summary(await load_scope(session, rules), son, section)

    async def son_memory(self, session: AsyncSession, rules: Rules, son: SonRow) -> str:
        return await son_memory(await load_scope(session, rules), son, full=True)

    async def mortal_view(self, session: AsyncSession, rules: Rules, mortal: EntityRow) -> str:
        return render(PromptId.MORTAL_CONTEXT, await mortal_context(await load_scope(session, rules), mortal, full=True))


class AgentChildBirth:
    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    async def birth_child(self, parent_son_id: int, inspiration: str, co_parent_son_id: int | None) -> BornChild:
        son = await birth_child(self._runtime, parent_son_id, inspiration, co_parent_son_id)
        return BornChild(son_id=son.id, name=son.name, title=son.title, rarity_label=RARITY_LABELS[son.rarity])


class AgentWorldBirth:
    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    async def birth_world(self, order: WorldBirthOrder) -> BornWorld:
        plan = BirthPlan(
            world_type=order.world_type,
            inspiration=order.inspiration,
            star_id=order.star_id,
            parent_world_id=order.parent_world_id,
            new_star=order.new_star,
            son_id=order.son_id,
        )
        world = await birth_world(self._runtime, plan)
        return BornWorld(world_id=world.id, name=world.name, type_label=WORLD_TYPES[world.world_type].label)


def agent_tool_ports(runtime: AgentRuntime) -> ToolPorts:
    return ToolPorts(views=AgentReadViews(), child_birth=AgentChildBirth(runtime), world_birth=AgentWorldBirth(runtime))


def attach_toolkits(runtime: AgentRuntime) -> AgentRuntime:
    runtime.toolkits = Toolkits(runtime.database, ports=agent_tool_ports(runtime), publish=runtime.publish, rules=runtime.rules_override)
    return runtime
