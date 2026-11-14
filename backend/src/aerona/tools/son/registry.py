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
from aerona.tools.son import (
    ages,
    agrarian,
    arts,
    bloodline,
    climes,
    collective,
    cosmography,
    cosmos,
    crafts,
    customs,
    cycles,
    death,
    disease,
    divinity,
    dominion,
    evolution,
    faith,
    flora,
    folk,
    folkways,
    gatherings,
    heavens,
    influence,
    intervention,
    kin,
    knowledge,
    land,
    language,
    law_depth,
    lineage,
    lore,
    made_kinds,
    materials,
    memory,
    military,
    mortals,
    mythic,
    names,
    operations,
    places,
    prayer,
    read,
    regime,
    regions,
    resources,
    sacred,
    structures,
    tongues,
    trade,
    treaties,
    urban,
    urban_depth,
    war,
    works,
    world_works,
)
from aerona.tools.son.availability import SonWorldState, condition_holds, star_lines
from aerona.tools.son.creation import creation_specs, example_cost
from aerona.tools.son.creation_rules import cheap_creation

SonSpec = ToolSpec[SonCall, Any]
FAMILIES: tuple[Callable[[], list[SonSpec]], ...] = (
    read.specs,
    memory.specs,
    language.specs,
    kin.specs,
    mortals.specs,
    prayer.specs,
    creation_specs,
    resources.specs,
    trade.specs,
    influence.specs,
    knowledge.specs,
    flora.specs,
    intervention.specs,
    disease.specs,
    dominion.specs,
    mythic.specs,
    tongues.specs,
    evolution.specs,
    urban_depth.specs,
    law_depth.specs,
    collective.specs,
    made_kinds.specs,
    cycles.specs,
    regime.specs,
    agrarian.specs,
    operations.specs,
    sacred.specs,
    arts.specs,
    ages.specs,
    folkways.specs,
    climes.specs,
    crafts.specs,
    customs.specs,
    gatherings.specs,
    war.specs,
    military.specs,
    treaties.specs,
    bloodline.specs,
    death.specs,
    faith.specs,
    cosmos.specs,
    heavens.specs,
    world_works.specs,
    cosmography.specs,
    urban.specs,
    folk.specs,
    materials.specs,
    structures.specs,
    lore.specs,
    places.specs,
    land.specs,
    regions.specs,
    works.specs,
    divinity.specs,
    lineage.specs,
    names.specs,
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
