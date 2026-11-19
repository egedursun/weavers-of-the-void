from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

E = RuleGroup.ECONOMY


@dataclass(frozen=True)
class EndowmentRules:
    income_pct: int = rule(5, 0, 50, E, "Share of its capital an endowment yields each epoch for its beneficiary")
    skim_chance_pct: int = rule(10, 0, 100, E, "Chance each epoch that a trustee skims part of an endowment's income")
    skim_share_pct: int = rule(30, 0, 100, E, "Share of the income a skimming trustee keeps")
    renown_per_epoch: int = rule(2, 0, 50, E, "Renown a living founder gains each epoch their endowment serves")
    confiscation_risk_pct: int = rule(5, 0, 100, E, "Chance each epoch that a realm in debt confiscates an unsheltered endowment in its lands")
    effect_per_income: int = rule(10, 1, 1000, E, "Income an endowment pays for each point it moves the town it serves")
    audit_honour: int = rule(10, 0, 100, E, "Honour a trustee loses when an audit finds what they skimmed")
    dark_age_keep_pct: int = rule(50, 0, 100, E, "Share by which an endowed institution lowers the chance its town forgets knowledge in a dark age")
