from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class DisastersRules:
    cap: int = rule(2, 0, 20, RuleGroup.POPULATION_AND_GROWTH, "Maximum natural events per epoch")
    earthquake_chance: int = rule(8, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Earthquake in a mountainous region (%)")
    flood_chance: int = rule(6, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Flood on the coast (%)")
    storm_chance: int = rule(6, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Storm on the coast (%)")
    drought_chance: int = rule(10, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Drought in a barren region (%)")
    region_plague_population: int = rule(3000, 0, 10000000, RuleGroup.POPULATION_AND_GROWTH, "Region population at which plague can be a natural event")
    region_plague_chance: int = rule(6, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Plague in a crowded region (%)")
    city_plague_crowd_floor: int = rule(3000, 0, 10000000, RuleGroup.POPULATION_AND_GROWTH, "Minimum crowding for city plague")
    city_plague_chance: int = rule(10, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Plague in a crowded city (%)")
    hungry_plague_chance: int = rule(12, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Plague in a hungry city (%)")
    war_plague_chance: int = rule(8, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Plague in a city at war (%)")
    plague_spread_chance: int = rule(35, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Plague jumps to a neighbour along links (%)")
    plague_spread_medicine_chance: int = rule(18, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Plague jumps to one who knows medicine (%)")
    law_mult: int = rule(2, 1, 20, RuleGroup.POPULATION_AND_GROWTH, "Natural-event frequency multiplier under the disaster law (times)")
    drought_fertility_threshold: int = rule(35, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Drought can occur in a region with fertility below this")
    plague_crowd_max_pct: int = rule(5, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Maximum contribution of crowding to region plague chance (%)")
    plague_crowd_divisor: int = rule(
        1000000, 1000, 1000000000, RuleGroup.POPULATION_AND_GROWTH, "Crowding contribution to region plague: population / this number"
    )
    severity_base: int = rule(30, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Base of natural-event severity")
    severity_die: int = rule(50, 1, 100, RuleGroup.POPULATION_AND_GROWTH, "Die added to natural-event severity (1\u2013X)")
    scale_divisor: int = rule(70, 1, 1000, RuleGroup.POPULATION_AND_GROWTH, "Effect strength of a natural event: severity / this number")
    city_plague_top_pct: int = rule(80, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Cities that can see plague: the world's top X% most populous")
    city_plague_always_population: int = rule(40000, 0, 100000000, RuleGroup.POPULATION_AND_GROWTH, "A city this populous can always see plague (people)")
    city_plague_min_population: int = rule(
        1500, 0, 10000000, RuleGroup.POPULATION_AND_GROWTH, "Minimum population of a city that can see plague (even if hungry or at war)"
    )
    plague_spread_epochs: int = rule(1, 0, 20, RuleGroup.POPULATION_AND_GROWTH, "Period over which plague spreads along routes (plagues of the last X epochs)")
    plague_spread_severity_pct: int = rule(
        60, 0, 100, RuleGroup.POPULATION_AND_GROWTH, "Severity of plague transmitted along routes (% of the original plague)"
    )
