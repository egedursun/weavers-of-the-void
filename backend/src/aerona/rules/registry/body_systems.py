from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.BODY


@dataclass(frozen=True)
class BodySystemRules:
    tolerance_harm_per_point: int = rule(2, 0, 20, G, "Prosperity a town loses for each ten points its world lies past what its people's bodies bear")
    adaptation_per_epoch: int = rule(2, 0, 20, G, "How far a people's tolerance moves toward the world it lives on each epoch")
    equipment_ease_pct: int = rule(40, 0, 100, G, "Share of the strain of a world past their limits a people's suits and equipment take away (%)")
    augment_ease_pct: int = rule(30, 0, 100, G, "Share of that strain made parts fitted to a people's folk take away (%)")
    grown_ease_pct: int = rule(30, 0, 100, G, "Share of that strain organs grown in a people's folk take away (%)")
    power_ease_pct: int = rule(25, 0, 100, G, "Share of that strain the powers of a people's folk take away (%)")
    rite_ease_pct: int = rule(20, 0, 100, G, "Share of that strain the rites a people keeps take away (%)")
    equipment_cost: int = rule(1, 0, 20, G, "Prosperity a town spends each epoch keeping its folk in equipment against a world past their limits")
    augment_cost: int = rule(2, 0, 20, G, "Prosperity a town spends each epoch keeping the made parts of its folk")
    grown_cost: int = rule(2, 0, 20, G, "Prosperity a town spends each epoch keeping the grown organs of its folk")
    power_cost: int = rule(1, 0, 20, G, "Prosperity a town spends each epoch on the powers that carry its folk past their limits")
    rite_cost: int = rule(1, 0, 20, G, "Prosperity a town spends each epoch on the rites that carry its folk past their limits")
    sensitivity_reaction_pct: int = rule(50, 0, 100, G, "Chance each epoch that a being meets what it is sensitive to when its town holds it (%)")
    low_gravity_wear: int = rule(1, 0, 20, G, "Health a being of a heavier world loses each epoch it lives on a lighter one")
    system_loss_capacity_pct: int = rule(30, 0, 100, G, "Excess past a tolerance at which a body system fails")
    margin: int = rule(25, 0, 100, G, "How far past the world it arose on a people's body bears at first")
