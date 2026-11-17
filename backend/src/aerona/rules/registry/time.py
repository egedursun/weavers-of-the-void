from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class TimeRules:
    years_per_epoch: int = rule(50, 1, 100000, RuleGroup.EPOCH_FLOW, "Length of one epoch (years)")
    sampled_years: int = rule(5, 1, 100, RuleGroup.EPOCH_FLOW, "Years of each epoch the engine lives through one by one")
