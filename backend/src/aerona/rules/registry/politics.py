from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class PoliticsRules:
    faction_strength_weight: int = rule(200, 0, 1000000, RuleGroup.CIVILIZATION, "Regional dominance: weight per faction strength point")
    faction_sway_weight: int = rule(50, 0, 1000000, RuleGroup.CIVILIZATION, "Regional dominance: weight per faction sway point")
    faction_default: int = rule(30, 0, 100, RuleGroup.CIVILIZATION, "Regional dominance: faction with unknown strength or sway")
    cult_follower_share_pct: int = rule(30, 0, 1000, RuleGroup.CIVILIZATION, "Regional dominance: counted share of cult followers (%)")
    rule_chain_depth: int = rule(4, 0, 50, RuleGroup.CIVILIZATION, "Regional dominance: steps looked up in the rule chain")
    town_population: int = rule(2000, 1, 100000000, RuleGroup.CIVILIZATION, "Settlement tier: town population")
    city_population: int = rule(10000, 1, 100000000, RuleGroup.CIVILIZATION, "Settlement tier: city population")
    metropolis_population: int = rule(50000, 1, 100000000, RuleGroup.CIVILIZATION, "Settlement tier: great-city population")
    megacity_population: int = rule(1000000, 1, 1000000000, RuleGroup.CIVILIZATION, "Settlement tier: population of a city of millions")
    conurbation_population: int = rule(10000000, 1, 10000000000, RuleGroup.CIVILIZATION, "Settlement tier: conurbation population")
