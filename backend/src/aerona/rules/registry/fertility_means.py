from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

R = RuleGroup.POPULATION_AND_GROWTH


@dataclass(frozen=True)
class FertilityMeansRules(Spanned):
    prevention_reliability_pct: int = rule(50, 0, 100, R, "Reliability of a means of prevention newly found (%)")
    remedy_success_pct: int = rule(20, 0, 100, R, "Further births a reliable remedy, aid to conception or bearing for another brings to those who use it (%)")
    risk_pct: int = rule(5, 0, 100, R, "Risk to the body a means carries when newly found, and the chance in an epoch that hidden use comes to light (%)")
    ending_pct: int = rule(50, 0, 100, R, "Share of the births a reliable ending of pregnancy takes from those who use it (%)")
    discover_level: int = rule(2, 0, 10, R, "Level of medicine at which a people may find a means by learning rather than folk knowledge")
    discover_pct: int = rule(10, 0, 100, R, "Chance in an epoch that a people finds a means it lacks (%)")
    spread_pct: int = rule(10, 0, 100, R, "Chance in an epoch that a means passes along a trade route to a people that lacks it (%)")
    medicine_gain: int = rule(5, 0, 50, R, "Reliability a means learned by medicine gains for each level of medicine its people knows")
    policy_push: int = rule(10, 0, 100, R, "Use a population policy at full force moves in an epoch toward its aim")
    ban_force_pct: int = rule(60, 0, 100, R, "Force of a population policy at which it forbids the means that work against its aim (%)")
    drift: int = rule(5, 0, 100, R, "Use a tolerated means gains in an epoch, and a forbidden one loses")
