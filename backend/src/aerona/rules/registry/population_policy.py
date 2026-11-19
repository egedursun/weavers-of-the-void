from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

S = RuleGroup.POPULATION_AND_GROWTH


@dataclass(frozen=True)
class PopulationPolicyRules(Spanned):
    birth_reward_pct: int = rule(10, 0, 100, S, "Share by which a birth reward raises the chance of births where it is enforced in full")
    birth_tax_pct: int = rule(10, 0, 100, S, "Share by which a birth tax lowers the chance of births where it is enforced in full")
    child_limit_resistance: int = rule(30, 0, 100, S, "Chance each epoch that a child limit enforced in full meets resistance")
    expulsion_grievance: int = rule(40, 0, 100, S, "Unrest an expulsion enforced in full raises in a town, in tenths")
    enforcement_cost_per_point: int = rule(2, 0, 50, S, "Treasury a policy costs its holder each epoch for each point of enforcement")
    review_years: int = span(100, 1, 1000, S, "Years between the reviews in which a holder weighs whether its policy works")
    migration_share_pct: int = rule(5, 0, 100, S, "Share of a town's people a migration or expulsion instrument moves each epoch when enforced in full")
    health_sanitation: int = rule(5, 0, 100, S, "Sanitation a health campaign enforced in full adds to a town each epoch")
    review_step: int = rule(10, 0, 100, S, "Strength a policy gains when its numbers move against its aim, or loses when they overshoot")
    overshoot_pct: int = rule(20, 0, 100, S, "Change in numbers past which a policy is held to have overshot its aim")
    grievance_unrest: int = rule(60, 0, 100, S, "Mean unrest of the towns under a policy from which their grievance takes strength from it each epoch")
    adopt_pct: int = rule(10, 0, 100, S, "Chance each epoch that a realm without a policy adopts one when its numbers press on it")
    resistance_enforcement_loss: int = rule(10, 0, 100, S, "Enforcement a policy loses when it meets resistance")
