from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class MechanicsRules:
    resource_die_chance: int = rule(30, 0, 100, RuleGroup.ECONOMY, "Chance a resource whose maker chose no mechanic still carries a special rule (%)")
    resource_max: int = rule(2, 1, 6, RuleGroup.ECONOMY, "Most special rules one resource can carry")
    law_die_chance: int = rule(70, 0, 100, RuleGroup.ECONOMY, "Chance a natural law whose maker chose no working still gets a mechanical working (%)")
    weight_decaying: int = rule(30, 0, 1000, RuleGroup.ECONOMY, "Die weight of the decaying rule")
    weight_addictive: int = rule(20, 0, 1000, RuleGroup.ECONOMY, "Die weight of the addictive rule")
    weight_sentient: int = rule(10, 0, 1000, RuleGroup.ECONOMY, "Die weight of the sentient rule")
    weight_depletion_price: int = rule(15, 0, 1000, RuleGroup.ECONOMY, "Die weight of the depletion price rule")
    weight_fixed: int = rule(25, 0, 1000, RuleGroup.ECONOMY, "Die weight of the fixed amount rule")
    weight_sacred: int = rule(20, 0, 1000, RuleGroup.ECONOMY, "Die weight of the sacred rule (only when a god is tied to the resource)")
