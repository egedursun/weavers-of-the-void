from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

C = RuleGroup.COSMOS


@dataclass(frozen=True)
class WorldEndRules:
    frozen_epochs: int = rule(3, 1, 100, C, "Epochs a world lit only by its star lives on under a dead star before it freezes dead")
    end_cost: int = rule(1000, 0, 100000, C, "Essence the Creator spends to bring a world to its end")
    giant_epochs: int = rule(20, 1, 1000, C, "Epochs a giant star burns before it swells over its nearest worlds")
    giant_reach_pct: int = rule(80, 0, 1000, C, "Orbit, in hundredths, within which a swollen giant star swallows a world")
    impact_pct: int = rule(2, 0, 100, C, "A comet that crosses a world's sky strikes it and shatters it (%)")
    void_rifts: int = rule(5, 1, 100, C, "Rifts open on one world at once at which it sinks into the void")
    forgotten_epochs: int = rule(30, 1, 1000, C, "Epochs a world that once held peoples and now holds none lasts before it is forgotten")
