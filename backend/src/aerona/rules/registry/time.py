from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import EPOCH_YEARS, rule


@dataclass(frozen=True)
class TimeRules:
    years_per_epoch: int = rule(EPOCH_YEARS, 1, 100000, RuleGroup.EPOCH_FLOW, "Length of one epoch (years)")
    sampled_years: int = rule(5, 1, 100, RuleGroup.EPOCH_FLOW, "Years of each epoch the engine lives through one by one")
    socialising_cohesion_pct: int = rule(
        20, 0, 100, RuleGroup.MORTALS, "Cohesion a people gains each epoch for each share of its time it spends in company (%)"
    )
    mourning_ease_pct: int = rule(
        40, 0, 100, RuleGroup.MORTALS, "How much each share of time a people sets aside for mourning eases the grief of its mourners (%)"
    )
