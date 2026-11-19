from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

D = RuleGroup.DEATH_AND_RESURRECTION


@dataclass(frozen=True)
class DeathWorkRules:
    untended_disease_pct: int = rule(30, 0, 100, D, "Share by which untended remains in a plague worsen its outbreak and stir the town")
    role_standing: int = rule(50, 0, 100, D, "Purity below which a death role is avoided and above which it is honoured")
    treatment_cost: int = rule(5, 0, 100, D, "Wealth the treatment of one body costs its estate, scaled by the treatment")
    recruit_step: int = rule(1, 0, 20, D, "Workers an honoured death role gains each epoch and an avoided one loses")
    sanitation_per_ten_dead: int = rule(1, 0, 20, D, "Sanitation a town gains or loses for every ten of its dead treated, by the treatment")
    called_per_epoch: int = rule(1, 0, 10, D, "Mortals of a people who take up death work in an epoch where the work is not avoided")
    standing_match: int = rule(10, 0, 50, D, "Match weight a death worker gains where the work is honoured and loses where it is avoided")
