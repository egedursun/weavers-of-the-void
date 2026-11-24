from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

E = RuleGroup.ECONOMY


@dataclass(frozen=True)
class RuinedGroundRules:
    stone_pct: int = rule(25, 0, 200, E, "Stone and salvage a quarry or a salvage ground on ruined ground gains from the dressed stone of the ruins (%)")
