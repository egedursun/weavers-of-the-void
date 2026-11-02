from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class LimitsRules:
    population_floor: int = rule(10, 1, 100000, RuleGroup.POPULATION_AND_GROWTH, "Minimum population of settlements and communities")
    people_population_floor: int = rule(100, 1, 1000000, RuleGroup.POPULATION_AND_GROWTH, "Minimum population of a people")
    settlement_population_cap: int = rule(2000000, 1000, 1000000000, RuleGroup.POPULATION_AND_GROWTH, "Maximum population of a settlement")
    people_population_cap: int = rule(50000000, 1000, 2000000000, RuleGroup.POPULATION_AND_GROWTH, "Maximum population of a people")
    cult_follower_cap: int = rule(10000000, 1000, 2000000000, RuleGroup.RELIGION_AND_LANGUAGE, "Maximum followers of a cult")
    army_soldier_cap: int = rule(10000000, 1000, 2000000000, RuleGroup.WAR_AND_DIPLOMACY, "Maximum soldiers in an army")
    hp_cap: int = rule(300, 10, 100000, RuleGroup.HEROES_AND_MORTALS, "Maximum HP of a mortal or creature")
