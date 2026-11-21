from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

R = RuleGroup.RELIGION_AND_LANGUAGE


@dataclass(frozen=True)
class DivineConceptionsRules(Spanned):
    drift_per_epoch_pct: int = rule(2, 0, 100, R, "Chance in an epoch that a faith's conception of the divine shifts one step on one axis (%)")
    denied_god_crisis_pct: int = rule(30, 0, 100, R, "Strain a faith takes when a god it denies or calls a demon acts openly in its lands")
    syncretism_fit_pct: int = rule(50, 0, 100, R, "How far fitting conceptions ease the mixing of faiths, and an exclusive one hinders it (%)")
    theologian_pull_pct: int = rule(10, 0, 100, R, "Further chance of a shift for each theologian among a faith's clergy (%)")
    split_pct: int = rule(30, 0, 100, R, "Chance that a faith whose strain is full splits rather than changes its mind (%)")
