from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

S = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class DeparturesRules(Spanned):
    age_weight: int = rule(30, 0, 100, S, "How far old age weighs toward leaving office, at the end of a life (%)")
    scandal_weight: int = rule(40, 0, 100, S, "How far a scandal of the last epoch weighs toward leaving office (%)")
    return_chance_pct: int = rule(5, 0, 100, S, "Chance in an epoch that one who left office returns to it while it stands empty or weak (%)")
    retirement_age_share_pct: int = rule(80, 0, 100, S, "Share of a life at which custom retires the holders of lesser offices (%)")
    health_weight: int = rule(20, 0, 100, S, "How far a lasting wound or illness weighs toward leaving office (%)")
    failure_weight: int = rule(25, 0, 100, S, "How far a realm's lost stability weighs toward its ruler leaving (%)")
    leave_chance_pct: int = rule(20, 0, 100, S, "Share of the weight toward leaving that becomes the chance of leaving in an epoch (%)")
    pension: int = rule(5, 0, 100000, S, "Coin a realm pays each epoch to one who left office with a pension")
    rally_standing: int = rule(60, 0, 100, S, "Standing from which one who abdicated is a rallying point against the ruler after them")
    rally_stability_loss: int = rule(2, 0, 100, S, "Stability a realm loses in an epoch while one who abdicated stands as a rallying point")
    standing_per_year: int = rule(1, 0, 100, S, "Standing one who left office keeps for every year they sat in the seat, before the conditions add theirs")
    standing_decay: int = rule(3, 0, 100, S, "Standing one who left office loses in an epoch")
    scandal_unrest_relief: int = rule(10, 0, 100, S, "Unrest a resignation under scandal takes from the holder's seat")
    call_heed_pct: int = rule(70, 0, 100, S, "Chance a holder heeds a son's call to step aside (%)")
