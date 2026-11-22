from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

S = RuleGroup.SETTLEMENTS


@dataclass(frozen=True)
class DailyLifeRules:
    overwork_stress_pct: int = rule(20, 0, 100, S, "Stress a being gains each epoch for each ten points of work above the usual share, in tenths")
    leisure_happiness_pct: int = rule(10, 0, 100, S, "Mood a being gains each epoch for each ten points of leisure above the usual share, in tenths")
    care_disease_pct: int = rule(15, 0, 100, S, "Share of the gap between a town's sanitation and what its people's care customs keep that closes each epoch")
    servant_relief_pct: int = rule(30, 0, 100, S, "Load of housework a servant, made mind or construct lifts from a household")
    tourism_spend_pct: int = rule(5, 0, 100, S, "Share of a traveller's coin spent each epoch at the place it visits for pleasure")
    space_breach_trust_loss: int = rule(5, 0, 100, S, "Trust two peoples lose each epoch for each norm of distance, touch or posture they do not share")
    cleanliness_honour_loss: int = rule(3, 0, 100, S, "Honour a being loses when its means fall short of its people's standard of cleanliness")
    usual_housework: int = rule(10, 0, 100, S, "Share of a year that is the usual share of housework")
    usual_sleep: int = rule(25, 0, 100, S, "Share of a year spent asleep by beings whose biology sleeps")
    heavy_load: int = rule(60, 0, 100, S, "Housework load of a household above which its young lose schooling and its doers gain stress")
    burdened_hire_wealth: int = rule(40, 0, 1000, S, "Household wealth from which a household weighed down by its housework takes on help")
    load_schooling_loss: int = rule(1, 0, 100, S, "Education a young doer of a heavy household loses each epoch")
    load_stress: int = rule(2, 0, 100, S, "Stress a doer of a heavy household gains each epoch")
    dependant_load: int = rule(5, 0, 100, S, "Housework load each child, elder or sick member adds to a household")
    trend_drift: int = rule(1, 0, 100, S, "Points a people's leisure shares move each epoch toward what its folk pursue")
    tourism_coin_min: int = rule(1, 0, 1000000, S, "Least coin a visit spends before it is told as a season of travellers")
    bound_flight_pct: int = rule(20, 0, 100, S, "Chance each epoch that a servant bound without wage leaves the household of their own choice (%)")
    servant_wage: int = rule(2, 0, 1000, S, "Wage a household pays each epoch to a servant it takes into service")
