from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

S = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class RestorationRules(Spanned):
    memory_decay_per_epoch: int = rule(3, 0, 50, S, "Memory a fallen realm loses in an epoch while no one raises it again")
    movement_grievance_threshold: int = rule(50, 0, 100, S, "Unrest in the fallen realm's old lands at which its memory turns into a movement")
    old_law_stability_loss: int = rule(10, 0, 100, S, "Stability a restored realm loses for each old law that no longer fits")
    rising_memory: int = rule(60, 0, 100, S, "Memory a movement needs before it rises")
    rising_chance_pct: int = rule(20, 0, 100, S, "Chance in an epoch that a movement with enough memory rises (%)")
    resistance_stability: int = rule(60, 0, 100, S, "Stability of the realm holding the old lands at which it holds them against a rising")
    stir_memory: int = rule(20, 0, 100, S, "Memory a son stirs in a fallen realm")
    basis_memory: int = rule(10, 0, 100, S, "Memory each basis of a restoration adds when it is raised")
    old_law_cap: int = rule(5, 0, 50, S, "Old laws a restored realm takes back at most")
