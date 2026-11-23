from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

R = RuleGroup.REPUTATION
H = RuleGroup.HOUSES
S = RuleGroup.SETTLEMENTS


@dataclass(frozen=True)
class RenownAxisRules:
    mercy_surrender_pct: int = rule(10, 0, 100, R, "How much readier a besieged town is to yield to a commander renowned for mercy, at full renown (%)")
    justice_legitimacy: int = rule(5, 0, 50, R, "Legitimacy a ruler renowned for justice gains each epoch at full renown, with unrest falling as much")
    mercy_gain: int = rule(10, 0, 100, R, "Mercy renown gained for sparing a foe, a captive or one condemned, or for a pardon")
    justice_gain: int = rule(8, 0, 100, R, "Justice renown gained for a judgement given by the law, the more for punishing the powerful")


@dataclass(frozen=True)
class InheritanceRules:
    will_contest_pct: int = rule(20, 0, 100, H, "Chance kin left out of a will contest it when it is read (%)")
    seniority_dispute_pct: int = rule(15, 0, 100, H, "Chance the children of the dead dispute an inheritance passed to the eldest of the line (%)")


@dataclass(frozen=True)
class DwellingRules:
    stilt_flood_cut_pct: int = rule(60, 0, 100, S, "Share of flood harm to households that houses on stilts turn aside (%)")
    burrow_cold_cut_pct: int = rule(50, 0, 100, S, "Share of cold harm and siege hunger to households that burrows turn aside (%)")
