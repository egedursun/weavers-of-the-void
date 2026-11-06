from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class FaithRules:
    followers_per_faith: int = rule(50, 1, 100000, RuleGroup.RELIGION_AND_LANGUAGE, "Faith: every this many cult followers give 1 faith")
    pious_population_per_faith: int = rule(2000, 1, 10000000, RuleGroup.RELIGION_AND_LANGUAGE, "Faith: every this much pious population gives 1 faith")
    default_piety: int = rule(50, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Faith: piety of a community whose piety is unknown")
    other_worshipper: int = rule(2, 0, 1000, RuleGroup.RELIGION_AND_LANGUAGE, "Faith: contribution of every other worshipping entity")
    community_min: int = rule(
        1,
        0,
        1000,
        RuleGroup.RELIGION_AND_LANGUAGE,
        "Faith: minimum contribution of each worshipping people, settlement and cult (a small community's faith is not rounded to zero)",
    )
    multiplier_power_pct: int = rule(150, 100, 1000, RuleGroup.RELIGION_AND_LANGUAGE, "Effect of the faith-multiplier power (%)")
    cult_saturation: int = rule(
        20,
        0,
        100000,
        RuleGroup.RELIGION_AND_LANGUAGE,
        "Faith: a cult's contribution is linear up to this much faith, then grows with diminishing returns (0: always linear)",
    )
    cult_saturation_exponent_pct: int = rule(
        50, 1, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Faith: exponent of a cult's contribution beyond saturation (%; 100 linear, 50 square root)"
    )
    essence_income_cap_pct: int = rule(
        25, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "A son's essence income from faith is at most this share of their essence cap per epoch (0: unlimited)"
    )
