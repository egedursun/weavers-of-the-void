from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

R = RuleGroup.BODY


@dataclass(frozen=True)
class AgentlessConditionsRules(Spanned):
    age_rate_pct: int = rule(3, 0, 100, R, "Chance in an epoch that age brings a condition to a being past its onset, at the end of its life span (%)")
    diet_rate_pct: int = rule(2, 0, 100, R, "Chance in an epoch that a poor diet brings a condition, at the deepest want (%)")
    exposure_rate_pct: int = rule(2, 0, 100, R, "Chance in an epoch that foul air, water and soil bring a condition, at the worst fouling (%)")
    heredity_weight_pct: int = rule(30, 0, 100, R, "Chance in an epoch that a condition of a parent passes to a child, for each parent who bears it (%)")
    strain_rate_pct: int = rule(2, 0, 100, R, "Chance in an epoch that strain brings a condition, at the greatest strain (%)")
    aftermath_rate_pct: int = rule(3, 0, 100, R, "Chance in an epoch that a grave wound leaves a lasting condition after it heals (%)")
    unknown_rate_pct: int = rule(1, 0, 100, R, "Chance in an epoch that a condition arises with no cause anyone can find (%)")
    worsen_pct: int = rule(20, 0, 100, R, "Chance in an epoch that a worsening condition grows heavier (%)")
    ease_pct: int = rule(10, 0, 100, R, "Chance in an epoch that a condition eases, before medicine and folk knowledge (%)")
    medicine_ease_pct: int = rule(5, 0, 100, R, "Further chance of easing for each level of medicine the people knows (%)")
    lifespan_cost: int = rule(1, 0, 20, R, "Years of life span a condition takes in an epoch for each step of its severity")
    care_cost: int = rule(1, 0, 20, R, "Wealth the care of a condition costs in an epoch for each step of its severity")
    strain_floor: int = rule(60, 0, 100, R, "Stress at which strain begins to bring conditions")
    aftermath_severity: int = rule(4, 1, 5, R, "Severity of a healed wound that may leave a lasting condition")
