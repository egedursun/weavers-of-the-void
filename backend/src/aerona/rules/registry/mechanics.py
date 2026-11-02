from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class MechanicsRules:
    hint_chance: int = rule(100, 0, 100, RuleGroup.ECONOMY, "Chance a resource or law whose text plainly names a mechanic takes that mechanic (%)")
    resource_die_chance: int = rule(30, 0, 100, RuleGroup.ECONOMY, "Chance a resource whose text names no mechanic still carries a strange rule (%)")
    resource_max: int = rule(2, 1, 6, RuleGroup.ECONOMY, "Most strange rules one resource can carry")
    law_die_chance: int = rule(70, 0, 100, RuleGroup.ECONOMY, "Chance a natural law whose text names no mechanic still gets a mechanical working (%)")
    subtype_leaning_mult: int = rule(2, 1, 20, RuleGroup.ECONOMY, "Die weight multiplier for the mechanic the resource's subtype suggests")
    weight_decaying: int = rule(30, 0, 1000, RuleGroup.ECONOMY, "Die weight of the decaying rule")
    weight_addictive: int = rule(20, 0, 1000, RuleGroup.ECONOMY, "Die weight of the addictive rule")
    weight_sentient: int = rule(10, 0, 1000, RuleGroup.ECONOMY, "Die weight of the sentient rule")
    weight_depletion_price: int = rule(15, 0, 1000, RuleGroup.ECONOMY, "Die weight of the depletion price rule")
    weight_fixed: int = rule(25, 0, 1000, RuleGroup.ECONOMY, "Die weight of the fixed amount rule")
    weight_sacred: int = rule(20, 0, 1000, RuleGroup.ECONOMY, "Die weight of the sacred rule (only when a god is tied to the resource)")
