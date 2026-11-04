from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.sons import SonRow
from aerona.engine.gods.progress import power_ceiling
from aerona.prompts import SonToolId
from aerona.prompts.tools.context import ToolTextContext
from aerona.prompts.tools.son import CREATION_TOOLS
from aerona.rules.registry import Rules
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.ports import ToolPorts
from aerona.tools.framework.spec import ToolSpec
from aerona.tools.son import cosmos, death, influence, intervention, kin, knowledge, land, language, memory, places, prayer, read, regions, resources, war
from aerona.tools.son.availability import SonWorldState, condition_holds, star_lines
from aerona.tools.son.creation import creation_specs, example_cost
from aerona.tools.son.creation_rules import cheap_creation

SonSpec = ToolSpec[SonCall, Any]
FAMILIES: tuple[Callable[[], list[SonSpec]], ...] = (
    read.specs,
    memory.specs,
    language.specs,
    kin.specs,
    prayer.specs,
    creation_specs,
    resources.specs,
    influence.specs,
    knowledge.specs,
    intervention.specs,
    war.specs,
    death.specs,
    cosmos.specs,
    places.specs,
    land.specs,
    regions.specs,
)
PORT_TAGS: dict[str, Callable[[ToolPorts], bool]] = {
    "views": lambda ports: ports.views is not None,
    "child_birth": lambda ports: ports.child_birth is not None,
    "world_birth": lambda ports: ports.world_birth is not None,
}


def son_specs() -> list[SonSpec]:
    specs: list[SonSpec] = []
    for family in FAMILIES:
        specs.extend(family())
    return specs


def ports_allow(spec: SonSpec, ports: ToolPorts) -> bool:
    return all(PORT_TAGS[tag](ports) for tag in spec.tags if tag in PORT_TAGS)


def son_may_use(spec: SonSpec, son: SonRow, rules: Rules, state: SonWorldState, ports: ToolPorts) -> bool:
    minimum = spec.meta.minimum_rarity(rules)
    if minimum is not None and not son.rarity.at_least(minimum):
        return False
    return ports_allow(spec, ports) and condition_holds(SonToolId(spec.name), rules, state)


async def son_text_context(session: AsyncSession, rules: Rules, son: SonRow, spec: SonSpec) -> ToolTextContext:
    tool_id = SonToolId(spec.name)
    ceiling = power_ceiling(rules, son)
    if tool_id in CREATION_TOOLS:
        entity_type = CREATION_TOOLS[tool_id]
        cheap = await cheap_creation(session, rules, son, entity_type)
        return ToolTextContext(power_ceiling=ceiling, example_cost=example_cost(rules, son, entity_type, cheap))
    if tool_id is SonToolId.BIRTH_WORLD:
        return ToolTextContext(power_ceiling=ceiling, stars=await star_lines(session))
    return ToolTextContext(power_ceiling=ceiling)
