from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

R = RuleGroup.HOUSES


@dataclass(frozen=True)
class HonoursRules(Spanned):
    prestige_per_rank: int = rule(5, 0, 50, R, "Renown an honour gives its holder for each step of its rank, at full worth")
    sale_worth_loss_pct: int = rule(20, 0, 100, R, "Worth an honour kind loses each time it is sold or given to a favourite (%)")
    loyalty_gain: int = rule(10, 0, 100, R, "Goodwill a holder feels toward the one who honoured them")
    deed_floor: int = rule(10, 0, 100, R, "Size of a deed its people praise at which a conferrer considers honouring it")
    rank_step: int = rule(4, 0, 50, R, "Size a deed needs beyond the floor for each step of an honour's rank above the first")
    confer_cap: int = rule(1, 0, 100, R, "Honours a conferrer grants at most in an epoch")
    pension_points: int = rule(2, 0, 50, R, "Wealth a pension pays its holder each epoch from the conferrer's purse")
    land_points: int = rule(10, 0, 100, R, "Wealth a grant of land gives its holder when the honour is conferred")
    favour_pct: int = rule(5, 0, 100, R, "Chance in an epoch that a greedy head sells an honour to the richest who has done nothing for it (%)")
    revoke_infamy: int = rule(15, 0, 100, R, "Infamy a holder gains when an honour is taken back")
