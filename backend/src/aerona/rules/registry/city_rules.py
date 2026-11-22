from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

S = RuleGroup.SETTLEMENTS


@dataclass(frozen=True)
class CityRulesRules(Spanned):
    fire_spread_cut_pct: int = rule(30, 0, 100, S, "Share of a town's fire risk that fire spacing or a required stone build cuts at full strength (%)")
    build_cost_rise_pct: int = rule(15, 0, 200, S, "Rise in the cost of building in a town for each land use rule at full strength (%)")
    refuse_disease_cut_pct: int = rule(20, 0, 100, S, "Sanitation a town gains from refuse taken away at full coverage")
    lighting_crime_cut_pct: int = rule(15, 0, 100, S, "Crime lit streets cut at full coverage")
    join_tie_threshold: int = rule(70, 0, 100, S, "Ties at which two settlements of one region grow into one conurbation")
    evasion_per_land_value_pct: int = rule(10, 0, 100, S, "Evasion of a weakly enforced rule for each point of land value, in tenths (%)")
    service_cost_per_thousand: int = rule(5, 0, 1000, S, "Treasury a service costs in an epoch for each thousand people it covers fully")
    lighting_prosperity: int = rule(3, 0, 100, S, "Prosperity lit streets bring through longer trade and leisure at full coverage")
    green_desirability: int = rule(10, 0, 100, S, "Desirability a green share rule lends a district at full strength")
    frontage_desirability: int = rule(5, 0, 100, S, "Desirability a frontage rule lends a district at full strength")
    split_unrest_gap: int = rule(40, 0, 100, S, "Gap in unrest between a member and the core at which a conurbation splits")
    rebuild_condition: int = rule(30, 0, 100, S, "Condition below which a district of a town with rules is rebuilt to plan")
    rebuild_cost: int = rule(200, 0, 100000, S, "Treasury a planned rebuild costs a town")
    service_start_chance_pct: int = rule(10, 0, 100, S, "Chance in an epoch that a town founds a service it lacks (%)")
    enforcement_follow_pct: int = rule(40, 0, 100, S, "Share of the way a land use rule's enforcement moves each epoch toward the order its town keeps (%)")
    budget_follow_pct: int = rule(50, 0, 100, S, "Share of the way a service's budget moves each epoch toward what covering its people fully costs (%)")
    quality_step: int = rule(10, 0, 100, S, "Quality a fully paid service gains in an epoch, and an unpaid one loses")
    rule_start_chance_pct: int = rule(5, 0, 100, S, "Chance in an epoch that a crowded town sets a land use rule it lacks (%)")
