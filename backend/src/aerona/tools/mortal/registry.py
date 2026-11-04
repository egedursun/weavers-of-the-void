from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.civilization import unlocked
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.civilization import TierCapability
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.prompts import MortalToolId
from aerona.prompts.tools.context import ToolTextContext
from aerona.rules.registry import Rules
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.ports import ToolPorts
from aerona.tools.framework.spec import ToolSpec
from aerona.tools.mortal import (
    armies,
    barter,
    captivity,
    cosmos,
    creatures,
    diplomacy,
    heroes,
    knowledge,
    language,
    production,
    read,
    religion,
    ruler,
    trade,
    treaties,
    war,
)
from aerona.tools.mortal.support import civilization_tier, rules_a_realm, worships_dead_son

T = MortalToolId
MortalSpec = ToolSpec[MortalCall, Any]
COMMUNITIES = frozenset(COMMUNITY_TYPES)
NAMED = frozenset({EntityType.MORTAL})
COMMUNITIES_AND_NAMED = COMMUNITIES | NAMED

ACTOR_TYPES: dict[MortalToolId, frozenset[EntityType]] = {
    T.FOUND_SETTLEMENT: frozenset({EntityType.PEOPLE, EntityType.FACTION, EntityType.CULT}),
    T.SABOTAGE: frozenset({EntityType.FACTION, EntityType.CULT, EntityType.MORTAL}),
    T.BUILD_SPY_NETWORK: frozenset({EntityType.FACTION, EntityType.CULT, EntityType.MORTAL, EntityType.PEOPLE, EntityType.SETTLEMENT}),
    T.PREACH: frozenset({EntityType.CULT}),
    T.DENY_GOD: frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.FACTION, EntityType.CULT}),
    T.PROPHESY: frozenset({EntityType.MORTAL, EntityType.CULT}),
    T.GO_ON_ADVENTURE: NAMED,
    T.CHALLENGE_GOD: NAMED,
    T.ESCAPE: NAMED,
    T.ADOPT: NAMED,
    T.ENACT_LAW: NAMED,
    T.APPOINT_OFFICER: NAMED,
    T.SET_TAX: NAMED,
    T.EXPLORE_LAND: COMMUNITIES_AND_NAMED,
    T.RESURRECTION_RITE: COMMUNITIES_AND_NAMED,
    T.BUILD_SHIP: frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.FACTION}),
    T.TAME_SPECIES: frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.MORTAL, EntityType.FACTION}),
    T.PAY_RANSOM: COMMUNITIES,
    T.RESCUE_CAPTIVE: COMMUNITIES_AND_NAMED,
    T.RAISE_ARMY: COMMUNITIES,
    T.APPOINT_COMMANDER: COMMUNITIES,
    T.BARTER: COMMUNITIES_AND_NAMED,
    T.LEND: COMMUNITIES_AND_NAMED,
    T.REPAY_DEBT: COMMUNITIES_AND_NAMED,
}

TIER_GATES: dict[MortalToolId, TierCapability] = {
    T.FIND_ROUTE: TierCapability.ROUTE_SEARCH,
    T.BUILD_SHIP: TierCapability.SHIPBUILDING,
    T.LAUNCH_EXPEDITION: TierCapability.EXPEDITION,
    T.EXPLORE_LAND: TierCapability.EXPLORATION,
    T.LEND: TierCapability.LOAN,
}


@dataclass(frozen=True)
class MortalState:
    actor_type: EntityType
    tier: int
    worships_dead_son: bool
    rules_realm: bool = False


Condition = Callable[[Rules, MortalState], bool]

CONDITIONS: dict[MortalToolId, Condition] = {
    T.COIN_WORDS: lambda rules, _state: rules.mortal_tools.coin_word_per_epoch > 0,
    T.DISCOVER_RESOURCE: lambda rules, _state: rules.mortal_tools.discover_resource_per_epoch > 0,
    T.CLAIM_RESOURCE: lambda rules, _state: rules.mortal_tools.claim_per_epoch > 0,
    T.WORSHIP: lambda rules, _state: rules.mortal_tools.worship_per_epoch > 0,
    T.PRAY_TO_CREATOR: lambda rules, _state: rules.mortal_tools.pray_creator_per_epoch > 0,
    T.LEARN_KNOWLEDGE: lambda rules, _state: rules.mortal_tools.learn_per_epoch > 0,
    T.PROPHESY: lambda rules, _state: rules.mortal_tools.prophesy_per_epoch > 0,
    T.APPOINT_COMMANDER: lambda rules, _state: rules.mortal_tools.appoint_commander_per_epoch > 0,
    T.ADOPT: lambda rules, _state: rules.mortal_tools.adopt_per_epoch > 0,
    T.EXPLORE_LAND: lambda rules, _state: rules.exploration.tool_per_epoch > 0,
    T.RESURRECTION_RITE: lambda rules, state: rules.death.rite_per_epoch > 0 and state.worships_dead_son,
    T.ENACT_LAW: lambda rules, state: rules.mortal_tools.enact_law_per_epoch > 0 and state.rules_realm,
    T.APPOINT_OFFICER: lambda rules, state: rules.mortal_tools.appoint_officer_per_epoch > 0 and state.rules_realm,
    T.SET_TAX: lambda rules, state: rules.mortal_tools.set_tax_per_epoch > 0 and state.rules_realm,
    T.PROPOSE_TREATY: lambda rules, state: rules.mortal_tools.propose_treaty_per_epoch > 0 and (state.rules_realm or state.actor_type is not EntityType.MORTAL),
    T.BREAK_TREATY: lambda _rules, state: state.rules_realm or state.actor_type is not EntityType.MORTAL,
}

FAMILIES: tuple[Callable[[], list[MortalSpec]], ...] = (
    read.specs,
    language.specs,
    production.specs,
    trade.specs,
    war.specs,
    diplomacy.specs,
    religion.specs,
    knowledge.specs,
    heroes.specs,
    cosmos.specs,
    creatures.specs,
    captivity.specs,
    armies.specs,
    barter.specs,
    ruler.specs,
    treaties.specs,
)


def mortal_specs() -> list[MortalSpec]:
    specs: list[MortalSpec] = []
    for family in FAMILIES:
        specs.extend(family())
    return specs


async def mortal_state(session: AsyncSession, rules: Rules, actor: EntityRow) -> MortalState:
    del rules
    return MortalState(actor.entity_type, await civilization_tier(session, actor), await worships_dead_son(session, actor), await rules_a_realm(session, actor))


def mortal_may_use(spec: MortalSpec, actor: EntityRow, rules: Rules, state: MortalState, ports: ToolPorts) -> bool:
    tool_id = MortalToolId(spec.name)
    allowed = ACTOR_TYPES.get(tool_id)
    if allowed is not None and actor.entity_type not in allowed:
        return False
    capability = TIER_GATES.get(tool_id)
    if capability is not None and not unlocked(rules, state.tier, capability):
        return False
    if "views" in spec.tags and ports.views is None:
        return False
    condition = CONDITIONS.get(tool_id)
    return condition is None or condition(rules, state)


def mortal_text_context(_spec: MortalSpec) -> ToolTextContext:
    return ToolTextContext()
