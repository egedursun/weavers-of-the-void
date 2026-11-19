from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

S = RuleGroup.POPULATION_AND_GROWTH


@dataclass(frozen=True)
class UnionsAndBirthRules:
    scandal_shame: int = rule(
        15, 0, 100, S, "Honour lost by those whose relation goes against a forbidden or discouraged norm of their people when it comes out"
    )
    persecution_flight_pct: int = rule(10, 0, 100, S, "Chance those caught in a relation their people forbids flee to another people")
    complication_base_pct: int = rule(8, 0, 100, S, "Chance of a complication at a birth at the usual risk of the bearer's people")
    attendant_care_pct: int = rule(50, 0, 100, S, "Share of the chance of a complication taken away by an attendant at the birth")
    recognition_cost: int = rule(10, 0, 100, S, "Wealth a parent pays to have a child recognised by payment, before the rule's own cost")
    scandal_pct: int = rule(30, 0, 100, S, "Chance each epoch that a relation against a forbidden or discouraged norm comes out, doubled under a forbidden one")
    sanction_fine: int = rule(10, 0, 100, S, "Wealth taken by a fine for a relation against the norms of a people")
    shun_relation: int = rule(15, 0, 100, S, "Friendship the enforcers lose toward those they shun")
    norm_drift_pct: int = rule(5, 0, 100, S, "Chance each epoch that a norm of intimacy moves one step toward what the values of its people hold")
    restraint_vow_pct: int = rule(20, 0, 100, S, "Chance each epoch that one bound by a custom of restraint vows it, at full strength of the custom")
    complication_harm: int = rule(15, 0, 100, S, "Health lost by a bearer in a complication of birth")
    recovery_health: int = rule(10, 0, 100, S, "Health a bearer regains through the care after birth that its people keeps")
