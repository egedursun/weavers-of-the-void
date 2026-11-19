from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.BODY


@dataclass(frozen=True)
class BodySystemRules:
    tolerance_harm_per_point: int = rule(2, 0, 20, G, "Prosperity a town loses for each ten points its world lies past what its people's bodies bear")
    adaptation_per_epoch: int = rule(2, 0, 20, G, "How far a people's tolerance moves toward the world it lives on each epoch")
    sensitivity_reaction_pct: int = rule(50, 0, 100, G, "Chance each epoch that a being meets what it is sensitive to when its town holds it (%)")
    low_gravity_wear: int = rule(1, 0, 20, G, "Health a being of a heavier world loses each epoch it lives on a lighter one")
    system_loss_capacity_pct: int = rule(30, 0, 100, G, "Excess past a tolerance at which a body system fails")
    margin: int = rule(25, 0, 100, G, "How far past the world it arose on a people's body bears at first")
