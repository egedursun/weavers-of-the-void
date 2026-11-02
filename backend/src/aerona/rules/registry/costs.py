from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class CostsRules:
    summon_son: int = rule(30, 0, 500, RuleGroup.GOD_AND_SON_COSTS, "Summon a son (Creator)")
    bless_essence: int = rule(15, 0, 500, RuleGroup.GOD_AND_SON_COSTS, "Blessing (essence)")
    bless_hp: int = rule(15, 0, 500, RuleGroup.GOD_AND_SON_COSTS, "Blessing (HP)")
    bless_stat: int = rule(40, 0, 500, RuleGroup.GOD_AND_SON_COSTS, "Blessing (stat)")
    lightning: int = rule(10, 0, 500, RuleGroup.GOD_AND_SON_COSTS, "Lightning (smite)")
    revelation: int = rule(25, 0, 500, RuleGroup.GOD_AND_SON_COSTS, "Revelation")
    transform: int = rule(15, 0, 500, RuleGroup.GOD_AND_SON_COSTS, "Transform (son)")
    bear_child: int = rule(60, 0, 500, RuleGroup.GOD_AND_SON_COSTS, "Bear a child (son)")
    destroy: int = rule(25, 0, 500, RuleGroup.GOD_AND_SON_COSTS, "Destroy (son)")
    influence: int = rule(6, 0, 500, RuleGroup.GOD_AND_SON_COSTS, "Influence (son)")
    curse: int = rule(12, 0, 500, RuleGroup.GOD_AND_SON_COSTS, "Curse (son)")
    dream: int = rule(10, 0, 500, RuleGroup.GOD_AND_SON_COSTS, "Dream (son)")
    incite_war: int = rule(10, 0, 500, RuleGroup.GOD_AND_SON_COSTS, "Incite war (son)")
    declare_chosen: int = rule(14, 0, 500, RuleGroup.GOD_AND_SON_COSTS, "Declare a chosen one (son)")
    covenant: int = rule(0, 0, 500, RuleGroup.GOD_AND_SON_COSTS, "Covenant")
    anchor: int = rule(0, 0, 500, RuleGroup.GOD_AND_SON_COSTS, "Anchor")
    rejudge_fate: int = rule(0, 0, 500, RuleGroup.GOD_AND_SON_COSTS, "Re-judge Fate's debt or limbo, or retry Fate")
    override_verdict: int = rule(0, 0, 500, RuleGroup.GOD_AND_SON_COSTS, "Override a Fate verdict")
    retry_voices: int = rule(0, 0, 500, RuleGroup.GOD_AND_SON_COSTS, "Retry the voices of the peoples")
    retry_births: int = rule(0, 0, 500, RuleGroup.GOD_AND_SON_COSTS, "Retry the births of sensed worlds")
    edit_historian_view: int = rule(0, 0, 500, RuleGroup.GOD_AND_SON_COSTS, "Edit or delete a historian's account")
