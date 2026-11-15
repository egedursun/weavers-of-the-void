from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

L = RuleGroup.CIVILIZATION


@dataclass(frozen=True)
class LifecycleEndRules:
    revival_pct: int = rule(10, 0, 100, L, "Chance each epoch that a dormant ideology or rite is taken up again from its surviving texts (%)")
    revival_strength: int = rule(20, 1, 100, L, "Strength of the first hold of a dormant ideology taken up again from its texts")
    rediscover_pct: int = rule(3, 0, 100, L, "Chance each epoch that a forgotten theory is found again by a people that studies its field (%)")
    practice_epochs: int = rule(5, 1, 50, L, "Epochs after its last casting that a caster still counts as knowing a rite")
    corruption_pct: int = rule(100, 0, 200, L, "Share of the missing fidelity of a text that becomes the chance a rite reconstructed from it is corrupted (%)")
    corrupted_backlash: int = rule(20, 0, 100, L, "Backlash chance a corrupted rite gains (%)")
    eradication_epochs: int = rule(3, 1, 50, L, "Epochs a disease must go without any host before it is eradicated")
    banish_interest: int = rule(20, 0, 100, L, "Interest below which an outer being with no open breach and no cult is banished")
    return_pct: int = rule(10, 0, 100, L, "Share of the leak of its world that is the chance each epoch a banished outer being returns (%)")
    destroy_cost: int = rule(500, 0, 100000, L, "Essence the Creator spends to destroy an outer being for good")
    son_cost: int = rule(30, 0, 1000, L, "Essence a son spends to wake a dormant ideology, theory or rite from its texts")
