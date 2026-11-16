from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class InterventionCostsRules:
    miracle: int = rule(15, 0, 300, RuleGroup.INTERVENTIONS_IN_THE_MORTAL_WORLD, "Miracle")
    disaster: int = rule(20, 0, 300, RuleGroup.INTERVENTIONS_IN_THE_MORTAL_WORLD, "Disaster")
    teach_knowledge: int = rule(12, 0, 300, RuleGroup.INTERVENTIONS_IN_THE_MORTAL_WORLD, "Teach knowledge")
    curse: int = rule(15, 0, 300, RuleGroup.INTERVENTIONS_IN_THE_MORTAL_WORLD, "Curse (Creator intervention)")
    verb_act: int = rule(10, 0, 300, RuleGroup.INTERVENTIONS_IN_THE_MORTAL_WORLD, "An act of the Creator by one of the verbs of divine power")
    verb_strength: int = rule(30, 0, 100, RuleGroup.INTERVENTIONS_IN_THE_MORTAL_WORLD, "Strength of an act of the Creator by a verb of divine power")
