from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.civilization import unlocked
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.agent import TurnCounter
from aerona.domain.enums.civilization import TierCapability
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.prompts import MortalToolId
from aerona.prompts.tools.context import ToolTextContext
from aerona.rules.registry import Rules
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.ports import ToolPorts
from aerona.tools.framework.spec import ToolSpec
from aerona.tools.framework.turn import counter_value
from aerona.tools.mortal import (
    affairs,
    ages,
    agrarian,
    armies,
    arts,
    barter,
    belonging,
    captivity,
    climes,
    collective,
    cosmos,
    crafts,
    creatures,
    customs,
    cycles,
    diplomacy,
    dominion,
    eras,
    estates,
    evolution,
    folkways,
    gatherings,
    hearth,
    heroes,
    intrigue,
    justice,
    knowledge,
    language,
    law_depth,
    letters,
    lore,
    made_kinds,
    mythic,
    nature,
    oaths,
    operations,
    production,
    read,
    regime,
    religion,
    ruler,
    sacred,
    social,
    statecraft,
    titles,
    tongues,
    trade,
    treaties,
    urban_depth,
    war,
    works,
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
    T.PROPHESY: frozenset({EntityType.MORTAL, EntityType.CULT, EntityType.SPIRIT}),
    T.FOUND_SCHOOL: NAMED,
    T.SOCIALISE: NAMED,
    T.CHALLENGE_TO_CONTEST: NAMED,
    T.PERSUADE: NAMED,
    T.TRADE_LORE: COMMUNITIES_AND_NAMED,
    T.CHOOSE_METHOD: COMMUNITIES_AND_NAMED,
    T.TEND_HOME: NAMED,
    T.PLOT_SCHEME: frozenset({EntityType.MORTAL, EntityType.FACTION, EntityType.CULT}),
    T.PRESS_LEVERAGE: NAMED,
    T.SEIZE_TITLE: NAMED,
    T.BARGAIN_WITH_ESTATE: NAMED,
    T.PROPOSE_LAW: NAMED,
    T.ACCUSE: NAMED,
    T.ISSUE_DEMAND: NAMED,
    T.BACK_CRISIS: NAMED,
    T.ISSUE_MANDATE: NAMED,
    T.ASSIGN_TASK: NAMED,
    T.SEND_DISPATCH: frozenset(
        {EntityType.MORTAL, EntityType.POLITY, EntityType.SETTLEMENT, EntityType.PEOPLE, EntityType.FACTION, EntityType.CULT, EntityType.SPIRIT}
    ),
    T.BUY_WORKSHOP: COMMUNITIES_AND_NAMED,
    T.LAY_TRADE_POLICY: COMMUNITIES_AND_NAMED,
    T.SPECULATE: COMMUNITIES_AND_NAMED,
    T.DESIGN_RITE: NAMED,
    T.COMMISSION_ARTWORK: frozenset({*COMMUNITY_TYPES, EntityType.POLITY, EntityType.MORTAL}),
    T.GO_ON_ADVENTURE: NAMED,
    T.CHALLENGE_GOD: NAMED,
    T.ESCAPE: NAMED,
    T.ADOPT: NAMED,
    T.ENACT_LAW: NAMED,
    T.SWEAR_OATH: NAMED,
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

SPIRIT_TOOLS = frozenset({T.LOOK_AT_WORLD, T.INSPECT_ENTITY, T.SEARCH_ENTITIES, T.PROPHESY, T.SEND_DISPATCH, T.PRAY_TO_CREATOR})

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
    spent: Mapping[TurnCounter, int] = field(default_factory=dict)


Condition = Callable[[Rules, MortalState], bool]
C = TurnCounter
AGE_LIMITS: dict[MortalToolId, tuple[TurnCounter, Callable[[Rules], int]]] = {
    T.APPOINT_COMMANDER: (C.COMMANDER_APPOINTMENTS, lambda rules: rules.mortal_tools.appoint_commander_per_epoch),
    T.EXPLORE_LAND: (C.EXPLORATIONS, lambda rules: rules.exploration.tool_per_epoch),
    T.ADOPT: (C.ADOPTIONS, lambda rules: rules.mortal_tools.adopt_per_epoch),
    T.LEARN_KNOWLEDGE: (C.LEARNING, lambda rules: rules.mortal_tools.learn_per_epoch),
    T.FOUND_LANGUAGE: (C.LANGUAGES_FOUNDED, lambda rules: rules.mortal_tools.language_per_epoch),
    T.COIN_WORDS: (C.WORDS_COINED, lambda rules: rules.mortal_tools.coin_word_per_epoch),
    T.SWEAR_OATH: (C.OATHS_SWORN, lambda rules: rules.mortal_tools.swear_oath_per_epoch),
    T.CREATE_CULTURE: (C.CULTURES_CREATED, lambda rules: rules.mortal_tools.culture_per_epoch),
    T.DISCOVER_RESOURCE: (C.DISCOVERIES, lambda rules: rules.mortal_tools.discover_resource_per_epoch),
    T.CLAIM_RESOURCE: (C.CLAIMS, lambda rules: rules.mortal_tools.claim_per_epoch),
    T.WORSHIP: (C.WORSHIP_CHANGES, lambda rules: rules.mortal_tools.worship_per_epoch),
    T.PRAY_TO_CREATOR: (C.PRAYERS, lambda rules: rules.mortal_tools.pray_creator_per_epoch),
    T.PROPHESY: (C.PROPHECIES, lambda rules: rules.mortal_tools.prophesy_per_epoch),
    T.RESURRECTION_RITE: (C.RESURRECTION_RITES, lambda rules: rules.death.rite_per_epoch),
    T.ENACT_LAW: (C.LAWS_ENACTED, lambda rules: rules.mortal_tools.enact_law_per_epoch),
    T.APPOINT_OFFICER: (C.OFFICERS_APPOINTED, lambda rules: rules.mortal_tools.appoint_officer_per_epoch),
    T.SET_TAX: (C.TAXES_SET, lambda rules: rules.mortal_tools.set_tax_per_epoch),
    T.PROPOSE_TREATY: (C.TREATIES_PROPOSED, lambda rules: rules.mortal_tools.propose_treaty_per_epoch),
}

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
    lore.specs,
    ruler.specs,
    treaties.specs,
    oaths.specs,
    social.specs,
    works.specs,
    hearth.specs,
    intrigue.specs,
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
    belonging.specs,
    climes.specs,
    eras.specs,
    nature.specs,
    crafts.specs,
    customs.specs,
    gatherings.specs,
    letters.specs,
    titles.specs,
    estates.specs,
    justice.specs,
    statecraft.specs,
    affairs.specs,
)


def mortal_specs() -> list[MortalSpec]:
    specs: list[MortalSpec] = []
    for family in FAMILIES:
        specs.extend(family())
    return specs


async def mortal_state(session: AsyncSession, rules: Rules, actor: EntityRow) -> MortalState:
    del rules
    epoch = (await CosmosRepository(session).require_cosmos()).epoch
    spent = {counter: await counter_value(session, actor.id, epoch, counter) for counter, _cap in AGE_LIMITS.values()}
    return MortalState(
        actor.entity_type,
        await civilization_tier(session, actor),
        await worships_dead_son(session, actor),
        await rules_a_realm(session, actor),
        spent,
    )


def within_age_limit(tool_id: MortalToolId, rules: Rules, state: MortalState) -> bool:
    limit = AGE_LIMITS.get(tool_id)
    return limit is None or state.spent.get(limit[0], 0) < limit[1](rules)


def mortal_may_use(spec: MortalSpec, actor: EntityRow, rules: Rules, state: MortalState, ports: ToolPorts) -> bool:
    tool_id = MortalToolId(spec.name)
    allowed = ACTOR_TYPES.get(tool_id)
    if allowed is not None and actor.entity_type not in allowed:
        return False
    if actor.entity_type is EntityType.SPIRIT and tool_id not in SPIRIT_TOOLS:
        return False
    capability = TIER_GATES.get(tool_id)
    if capability is not None and not unlocked(rules, state.tier, capability):
        return False
    if "views" in spec.tags and ports.views is None:
        return False
    if not within_age_limit(tool_id, rules, state):
        return False
    condition = CONDITIONS.get(tool_id)
    return condition is None or condition(rules, state)


def mortal_text_context(_spec: MortalSpec) -> ToolTextContext:
    return ToolTextContext()
