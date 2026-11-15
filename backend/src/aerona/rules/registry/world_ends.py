from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

C = RuleGroup.COSMOS


@dataclass(frozen=True)
class WorldEndRules:
    frozen_epochs: int = rule(3, 1, 100, C, "Epochs a world lit only by its star lives on under a dead star before it freezes dead")
    end_cost: int = rule(1000, 0, 100000, C, "Essence the Creator spends to bring a world to its end")
