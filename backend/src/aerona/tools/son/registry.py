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
    agentless_conditions,
    ages,
    agrarian,
    arts,
    belonging,
    biology,
    bloodline,
    city_rules,
    climes,
    collective,
    competition,
    cosmography,
    cosmos,
    couplings,
    crafts,
    creature_groups,
    customs,
    cycles,
    death,
    deep,
    departures,
    disease,
    divine_conceptions,
    divine_powers,
    divinity,
    dominion,
    economic,
    eras,
    events,
    evolution,
    faith,
    feeling_spread,
    fertility_means,
    flora,
    folk,
    folkways,
    fortune,
    fossils,
    gatherings,
    governance,
    grave_goods,
    heavens,
    influence,
    interpretation,
    intervention,
    interworld,
    kin,
    kin_dynamics,
    kinds,
    knowledge,
    labour,
    land,
    language,
    law_depth,
    leader_cults,
    leagues,
    lifecycle_ends,
    lineage,
    living,
    lore,
    made_kinds,
    mass_weapons,
    materials,
    media,
    memory,
    military,
    minds,
    monetary,
    mortals,
    museums,
    mythic,
    names,
    natural_laws,
    nature,
    occupation_regimes,
    operations,
    person_honours,
    places,
    population,
    powers,
    prayer,
    prehistory,
    protected_nature,
    public_works,
    read,
    reckoning,
    referendums,
    regime,
    regions,
    resources,
    restoration,
    sacred,
    sea_waves,
    securities,
    space_weather,
    structures,
    tongues,
    trade,
    transform,
    treaties,
    urban,
    urban_depth,
    w52_agent_a,
    war,
    water,
    ways_of_nature,
    works,
    world_views,
    world_works,
)
from aerona.tools.son.availability import SonWorldState, condition_holds, star_lines
from aerona.tools.son.creation import creation_specs, example_cost
from aerona.tools.son.creation_rules import cheap_creation

SonSpec = ToolSpec[SonCall, Any]
FAMILIES: tuple[Callable[[], list[SonSpec]], ...] = (
    read.specs,
    events.specs,
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
    minds.specs,
    powers.specs,
    living.specs,
    fortune.specs,
    divine_powers.specs,
    natural_laws.specs,
    ages.specs,
    economic.specs,
    world_views.specs,
    biology.specs,
    lifecycle_ends.specs,
    prehistory.specs,
    transform.specs,
    couplings.specs,
    fossils.specs,
    museums.specs,
    folkways.specs,
    belonging.specs,
    climes.specs,
    space_weather.specs,
    water.specs,
    eras.specs,
    nature.specs,
    crafts.specs,
    kinds.specs,
    ways_of_nature.specs,
    customs.specs,
    population.specs,
    competition.specs,
    labour.specs,
    monetary.specs,
    securities.specs,
    leagues.specs,
    departures.specs,
    referendums.specs,
    reckoning.specs,
    leader_cults.specs,
    restoration.specs,
    occupation_regimes.specs,
    mass_weapons.specs,
    interworld.specs,
    city_rules.specs,
    protected_nature.specs,
    kin_dynamics.specs,
    feeling_spread.specs,
    w52_agent_a.specs,
    interpretation.specs,
    grave_goods.specs,
    agentless_conditions.specs,
    fertility_means.specs,
    person_honours.specs,
    sea_waves.specs,
    creature_groups.specs,
    divine_conceptions.specs,
    governance.specs,
    media.specs,
    public_works.specs,
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
    deep.specs,
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
