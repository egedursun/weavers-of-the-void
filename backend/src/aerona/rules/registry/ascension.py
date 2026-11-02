from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class AscensionRules:
    level: int = rule(9, 1, 100, RuleGroup.RARITY_TIERS, "Level required to ascend to the next rarity")
    renown: int = rule(90, 0, 100, RuleGroup.RARITY_TIERS, "Renown required to ascend to the next rarity")
    essence_cost: int = rule(90, 0, 1000, RuleGroup.RARITY_TIERS, "Essence cost of ascending to the next rarity")
