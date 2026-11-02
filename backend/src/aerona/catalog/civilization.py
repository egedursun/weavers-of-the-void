from collections.abc import Callable
from dataclasses import dataclass

from aerona.domain.enums.civilization import TierCapability
from aerona.domain.enums.entity import CivilizationTier
from aerona.rules.registry import Rules

T = TierCapability


@dataclass(frozen=True)
class TierUnlock:
    capability: TierCapability
    label: str
    tier: Callable[[Rules], int]


TIER_LABELS: dict[CivilizationTier, str] = {
    CivilizationTier.TRIBE: "Tribe",
    CivilizationTier.CITY_STATE: "City-state",
    CivilizationTier.KINGDOM: "Kingdom",
    CivilizationTier.WORLD_EMPIRE: "World empire",
    CivilizationTier.INTERSTELLAR_POWER: "Interstellar power",
    CivilizationTier.COSMIC_POWER: "Cosmic power",
}

TIER_UNLOCKS: dict[TierCapability, TierUnlock] = {
    unlock.capability: unlock
    for unlock in (
        TierUnlock(T.EXPEDITION, "Expeditions to other worlds", lambda rules: rules.civilization.unlock_expedition_tier),
        TierUnlock(T.COLONY, "Colonies on other worlds", lambda rules: rules.civilization.unlock_colony_tier),
        TierUnlock(T.CONQUEST, "Conquest expeditions", lambda rules: rules.civilization.unlock_conquest_tier),
        TierUnlock(T.ROUTE_SEARCH, "Searching for routes between worlds", lambda rules: rules.civilization.unlock_route_search_tier),
        TierUnlock(T.SHIPBUILDING, "Ships that sail between worlds", lambda rules: rules.civilization.unlock_shipbuilding_tier),
        TierUnlock(T.INTERWORLD_TREATY, "Interworld treaties", lambda rules: rules.civilization.unlock_treaty_tier),
        TierUnlock(T.FEDERATION, "Interworld federations", lambda rules: rules.civilization.unlock_federation_tier),
        TierUnlock(T.LOAN, "Lending to other communities", lambda rules: rules.civilization.unlock_loan_tier),
        TierUnlock(T.EXPLORATION, "Exploring unknown lands", lambda rules: rules.civilization.unlock_exploration_tier),
        TierUnlock(T.DEPOSIT_CLAIM, "Claiming the cosmic travel resource", lambda rules: rules.civilization.unlock_deposit_claim_tier),
    )
}


def required_tier(rules: Rules, capability: TierCapability) -> CivilizationTier:
    return CivilizationTier(max(CivilizationTier.TRIBE, min(max(CivilizationTier), TIER_UNLOCKS[capability].tier(rules))))


def unlocked(rules: Rules, tier: int, capability: TierCapability) -> bool:
    return tier >= required_tier(rules, capability)


def capabilities_at(rules: Rules, tier: int) -> list[TierCapability]:
    return [capability for capability in TierCapability if unlocked(rules, tier, capability)]
