from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

B = RuleGroup.BODY


@dataclass(frozen=True)
class BiologyVariantRules:
    bias_pct: int = rule(100, 0, 200, B, "Share of the leanings of its biology that a mind of a people or species takes on (%)")
    son_cost: int = rule(40, 0, 1000, B, "Essence a son spends to give a people or species a biology variant or take one away")
