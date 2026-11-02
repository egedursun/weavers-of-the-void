from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class ModifiersRules:
    decayed_add_drop_below: float = rule(0.5, 0, 100, RuleGroup.INTERCONNECTION, "An additive modifier is removed once decay shrinks it below this size")
    decayed_multiplier_drop_within_pct: int = rule(
        1, 0, 100, RuleGroup.INTERCONNECTION, "A multiplying modifier is removed once decay brings it this close to no effect (%)"
    )
