from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class TradeRules:
    route_prosperity: int = rule(3, 0, 100, RuleGroup.ECONOMY, "Prosperity a trade route gives each epoch")
    route_wealth: int = rule(3, 0, 100, RuleGroup.ECONOMY, "Wealth a trade route gives each epoch")
    knowledge_mult: int = rule(2, 1, 20, RuleGroup.ECONOMY, "Trade prosperity multiplier for those knowing trade (times)")
    prosperity_cap: int = rule(6, 0, 100, RuleGroup.ECONOMY, "Maximum prosperity trade routes give one community in one epoch (all routes together)")
    wealth_cap: int = rule(6, 0, 100, RuleGroup.ECONOMY, "Maximum wealth trade routes give one community in one epoch (all routes together)")
    barter_cap: int = rule(2, 0, 50, RuleGroup.ECONOMY, "Maximum resource barters established spontaneously per epoch")
    rivalry_war_chance: int = rule(
        15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "A people short of a strategic good goes to war to seize a weaker neighbour's source of it (%)"
    )
    barter_chance: int = rule(30, 0, 100, RuleGroup.ECONOMY, "Resource barter between neighbours begins (%)")
    coinage_min_wealth: int = rule(50, 0, 100, RuleGroup.ECONOMY, "Minimum prosperity or wealth of a community able to mint coins")
    currency_power: int = rule(3, 1, 12, RuleGroup.ECONOMY, "Power level of a currency")
    currency_might_base: int = rule(10, 0, 100, RuleGroup.ECONOMY, "Currency might: base")
    currency_might_die: int = rule(20, 1, 100, RuleGroup.ECONOMY, "Die added to currency might (1\u2013X)")
    shared_currency_prosperity: int = rule(2, 0, 100, RuleGroup.ECONOMY, "Per-epoch prosperity gain of trade partners using a shared currency")
    coinage_chance: int = rule(25, 0, 100, RuleGroup.ECONOMY, "A wealthy community mints coins (%)")
    currency_adopt_chance: int = rule(30, 0, 100, RuleGroup.ECONOMY, "A trade partner adopts the currency (%)")
    route_ease_floor_pct: int = rule(40, 0, 100, RuleGroup.ECONOMY, "Share of trade income kept on the hardest road (%)")
    scarcity_pct: int = rule(
        50, 0, 1000, RuleGroup.ECONOMY, "Stock of a strategic good, as a share of an epoch's need, below which a people wants to seize a source of it (%)"
    )
