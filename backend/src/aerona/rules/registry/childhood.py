from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

S = RuleGroup.POPULATION_AND_GROWTH


@dataclass(frozen=True)
class ChildhoodRules:
    infant_survival_pct: int = rule(85, 0, 100, S, "Chance an infant lives through an epoch under the usual care of its people")
    harsh_stress_pct: int = rule(20, 0, 100, S, "Stress a child gains each epoch at full weight of shame, punishment and ordeal, in tenths")
    play_cooperation_pct: int = rule(10, 0, 100, S, "Pull toward cooperation a child gains each epoch at full weight of play and peer groups, in tenths")
    labour_schooling_loss_pct: int = rule(30, 0, 100, S, "Share of a working child's schooling lost at full share of child labour")
    pedagogy_speed_pct: int = rule(20, 0, 100, S, "Education a child gains each epoch from a school or tradition at the fastest theory, in tenths")
    socialize_step: int = rule(2, 0, 100, S, "Points a child's values move each epoch toward what its people raises children to be")
    feeding_survival_shift: int = rule(5, 0, 100, S, "Survival an infant gains or loses for each step its feeding and carers stand from the usual")
    labour_output: int = rule(1, 0, 100, S, "Prosperity a town gains each epoch for each working child, in tenths")
