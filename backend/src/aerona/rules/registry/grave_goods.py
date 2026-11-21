from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

R = RuleGroup.DEATH_AND_RESURRECTION


@dataclass(frozen=True)
class GraveGoodsRules(Spanned):
    share_by_rank_pct: int = rule(10, 0, 100, R, "Share of the wealth and goods of the dead laid with them, raised by their renown (%)")
    rob_chance_per_value_pct: int = rule(5, 0, 100, R, "Chance in an epoch that a grave is robbed for every ten points of goods in it (%)")
    guard_cut_pct: int = rule(50, 0, 100, R, "Share of the chance of robbery each step of a grave's guard takes away (%)")
    sealed_value: int = rule(30, 0, 100, R, "Worth of goods at which the kin seal the grave")
    caught_pct: int = rule(30, 0, 100, R, "Chance that the guard or trap of a grave catches its robber (%)")
    curse_pct: int = rule(50, 0, 100, R, "Chance that a curse laid on a grave takes its robber, by the strength of magic in the land (%)")
    grief: int = rule(25, 0, 100, R, "Grievance the kin and people of the dead hold against one who robbed the grave")
    find_fidelity: int = rule(70, 0, 100, R, "Truth of the account of the past that a found grave gives")
    guard_cost: int = rule(5, 0, 100, R, "Wealth paid for each step of guard set over a grave")
    robbers: int = rule(50, 0, 10000, R, "Graves at most that robbers try in an epoch")
