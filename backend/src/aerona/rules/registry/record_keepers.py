from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

F = RuleGroup.FATE_AND_CHRONICLE


@dataclass(frozen=True)
class RecordKeeperRules:
    lettered_weight: int = rule(20, 0, 100, F, "Weight a scribe, sage, priest, journalist or scientist gets when a chronicler or historian is chosen")
    court_chronicler_weight: int = rule(30, 0, 100, F, "Weight a ruler's court chronicler gets when a chronicler or historian is chosen")
    writing_weight_pct: int = rule(50, 0, 200, F, "Share of a mortal's writing skill that counts when a chronicler or historian is chosen (%)")
    apprentice_weight: int = rule(40, 0, 100, F, "Weight an apprentice of the keeper who died gets when a successor is chosen")
    same_place_weight: int = rule(10, 0, 100, F, "Weight a mortal of the dead keeper's own place gets when a successor is chosen")
    recovered_age: int = rule(40, 1, 1000, F, "Age given to a keeper of an old age who is brought into the world from the written record")
    recovered_lifespan: int = rule(70, 1, 100000, F, "Lifespan given to a keeper of an old age who is brought into the world from the written record")
