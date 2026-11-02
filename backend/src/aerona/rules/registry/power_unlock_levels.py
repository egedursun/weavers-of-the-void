from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class PowerUnlockLevelsRules:
    power_1_unlock_level: int = rule(1, 1, 50, RuleGroup.GOD_AND_SON_COSTS, "Level at which the son's 1st power unlocks")
    power_2_unlock_level: int = rule(3, 1, 50, RuleGroup.GOD_AND_SON_COSTS, "Level at which the son's 2nd power unlocks")
    power_3_unlock_level: int = rule(5, 1, 50, RuleGroup.GOD_AND_SON_COSTS, "Level at which the son's 3rd power unlocks")
