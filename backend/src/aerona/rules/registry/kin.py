from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

S = RuleGroup.SETTLEMENTS


@dataclass(frozen=True)
class KinRules:
    help_share_pct: int = rule(
        20, 0, 100, S, "Share of a kin member's coin given each epoch to kin in need whom a duty of support binds, at full strength of the duty"
    )
    breach_shame: int = rule(10, 0, 100, S, "Honour lost by one who could keep a strong duty to kin in need and does not")
    group_exogamy_strength: int = rule(80, 0, 100, S, "Strength of exogamy a kin group of a descent form is founded with")
    split_size: int = rule(200, 2, 100000, S, "Members above which a kin group splits in two")
    title_hold_pct: int = rule(100, 0, 1000, S, "Members a kin group can grow by before it splits for each point of prestige of the titles its head holds (%)")
    need_wealth: int = rule(15, 0, 100, S, "Wealth below which a being is in need of its kin")
    duty_floor: int = rule(30, 0, 100, S, "Strength from which a duty to kin is felt as binding")
    exogamy_bar: int = rule(50, 0, 100, S, "Exogamy of a kin group from which its members may not wed one another")
    mourn_mood: int = rule(10, 0, 100, S, "Mood lost by kin a duty of mourning binds when one of theirs dies, at full strength of the duty")
    avenge_feud: int = rule(10, 0, 100, S, "Relation lost between the people of a killer and the people of the killed for each kin member bound to avenge")
    founding_strength: int = rule(50, 0, 100, S, "Strength of the duties seeded for a people from its kinship system")
