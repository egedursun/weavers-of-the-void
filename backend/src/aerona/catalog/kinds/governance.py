from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.polity import DecisionRule


@dataclass(frozen=True)
class DecisionRuleSpec:
    ruler_divisor: int
    council_divisor: int


DECISION_RULES: Mapping[DecisionRule, DecisionRuleSpec] = total(
    DecisionRule,
    {
        DecisionRule.AUTOCRATIC: DecisionRuleSpec(ruler_divisor=1, council_divisor=3),
        DecisionRule.COUNCIL: DecisionRuleSpec(ruler_divisor=2, council_divisor=1),
        DecisionRule.ASSEMBLY: DecisionRuleSpec(ruler_divisor=2, council_divisor=2),
        DecisionRule.DIVINE: DecisionRuleSpec(ruler_divisor=2, council_divisor=3),
    },
)
