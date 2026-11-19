from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

S = RuleGroup.ECONOMY


@dataclass(frozen=True)
class MediaRules(Spanned):
    reach_per_staff: int = rule(2, 0, 20, S, "Reach an outlet gains for each of its staff")
    trust_loss_on_exposure: int = rule(25, 0, 100, S, "Trust an outlet loses when an item it spread is found false")
    opinion_shift_pct: int = rule(15, 0, 100, S, "Approval an item at full reach and full slant moves in its audience, in tenths")
    record_decay_per_epoch: int = rule(3, 0, 50, S, "Condition a recorded item loses each epoch at no durability of its medium")
    censorship_cost: int = rule(10, 0, 100, S, "Treasury a realm pays each epoch for each outlet it keeps censored")
    evidence_weight_pct: int = rule(40, 0, 100, S, "Reliability a faithful record of a crime lends a case as evidence, at full accuracy")
    revenue_per_reach: int = rule(1, 0, 100, S, "Wealth an outlet brings its owner each epoch for each ten of reach, before trust")
    star_reach: int = rule(60, 0, 100, S, "Reach of an entertainment item at which the being it shows rises to renown")
    star_renown: int = rule(10, 0, 100, S, "Renown a being gains when an entertainment item shows it to a wide audience")
    found_pct: int = rule(10, 0, 100, S, "Chance each epoch that an old record still kept is found again")
    alarm_slant: int = rule(50, 1, 100, S, "Slant against a town from which news of it sends its townsfolk to hoard the good it is shortest of")
    alarm_strength_pct: int = rule(60, 0, 100, S, "Strength of the hoarding that alarming news at full reach and full slant sets off in its town")
    record_age_years: int = span(150, 0, 5000, S, "Years after which a kept record counts as old and may be found again")
