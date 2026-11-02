from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class SetupWizardRules:
    first_sons_min: int = rule(1, 1, 8, RuleGroup.GENESIS_WIZARD, "Wizard: minimum number of first sons")
    first_sons_max: int = rule(5, 1, 8, RuleGroup.GENESIS_WIZARD, "Wizard: maximum number of first sons")
    first_sons_top_rarity_rank: int = rule(4, 0, 5, RuleGroup.GENESIS_WIZARD, "Wizard: highest rarity rank a first son may have (0 common to 5 mythic)")
    magic: int = rule(50, 0, 100, RuleGroup.GENESIS_WIZARD, "Wizard: default magic density")
    darkness: int = rule(50, 0, 100, RuleGroup.GENESIS_WIZARD, "Wizard: default darkness")
    peoples: int = rule(2, 1, 50, RuleGroup.GENESIS_WIZARD, "Wizard: default number of initial peoples")
    peoples_max: int = rule(5, 1, 50, RuleGroup.GENESIS_WIZARD, "Wizard: maximum initial peoples")
    small_cosmos_worlds: int = rule(1, 0, 20, RuleGroup.GENESIS_WIZARD, "Small cosmos: worlds added at genesis")
    large_cosmos_worlds: int = rule(2, 0, 20, RuleGroup.GENESIS_WIZARD, "Large cosmos: worlds added at genesis")
    setting_pull_pct: int = rule(50, 0, 100, RuleGroup.GENESIS_WIZARD, "After genesis, regions' magic/danger is pulled toward the setting by this percentage")
