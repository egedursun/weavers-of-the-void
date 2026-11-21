from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

S = RuleGroup.ENVIRONMENT


@dataclass(frozen=True)
class ProtectedNatureRules(Spanned):
    use_cut_per_strength_pct: int = rule(80, 0, 100, S, "Share of a banned use a protection at full strength stops (%)")
    recovery_per_epoch: int = rule(3, 0, 50, S, "Forest, wild land and wildlife a fully protected area regains in an epoch (%)")
    poaching_per_price_pct: int = rule(10, 0, 100, S, "Poaching a protected area draws for each point of want around it, in tenths (%)")
    reintroduction_success_pct: int = rule(40, 0, 100, S, "Chance in an epoch that a reintroduction takes in a land the species left (%)")
    displacement_grievance: int = rule(20, 0, 100, S, "Unrest a fully protected area brings to towns whose livelihood it bans")
    warden_strength: int = rule(5, 0, 100, S, "Strength each warden lends a protected area")
    poached_at: int = rule(30, 0, 100, S, "Poaching at which a protected area is told to be poached")
    habitat_fit: int = rule(30, 0, 100, S, "Fit a land must offer a species before it can be reintroduced there")
    reintroduced_abundance: int = rule(5, 0, 100, S, "Abundance a reintroduced species starts with in a land")
    livelihood_prosperity: int = rule(3, 0, 100, S, "Prosperity a town loses for each livelihood a full protection bans around it")
    conservation_loss_pct: int = rule(50, 0, 200, S, "Weight of lost wildlife and forest in the push for a conservation movement (%)")
