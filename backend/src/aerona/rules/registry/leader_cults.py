from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

S = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class LeaderCultsRules(Spanned):
    legitimacy_per_intensity_pct: int = rule(20, 0, 100, S, "Legitimacy a cult at full intensity lends its leader's realm in an epoch, in tenths (%)")
    sincerity_decay: int = rule(5, 0, 50, S, "Sincerity the public loses in an epoch a cult runs ahead of the realm's results")
    cost_per_instrument: int = rule(3, 0, 50, S, "Treasury each instrument of a cult costs the realm in an epoch")
    apotheosis_chance_pct: int = rule(5, 0, 100, S, "Chance at full intensity that a dead leader's cult turns into a faith (%)")
    start_chance_pct: int = rule(3, 0, 100, S, "Chance in an epoch that the sole ruler of a realm has a cult raised to them (%)")
    intensity_step: int = rule(5, 0, 50, S, "Points a cult's intensity moves in an epoch toward what its instruments raise")
    dissent_relief: int = rule(5, 0, 100, S, "Unrest a cult at full intensity takes from the seat of its realm in an epoch")
    pass_on_from: int = rule(50, 0, 100, S, "Intensity from which a dead leader's cult passes to an heir")
