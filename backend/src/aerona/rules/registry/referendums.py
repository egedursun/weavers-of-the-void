from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

S = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class ReferendumsRules(Spanned):
    petition_threshold_pct: int = rule(10, 0, 100, S, "Support a movement needs before its petition calls a vote of the people on its cause")
    ignore_legitimacy_loss: int = rule(20, 0, 100, S, "Legitimacy a ruler loses for ignoring a vote that did not bind them")
    campaign_shift_pct: int = rule(10, 0, 100, S, "Points of support a side gains for each hundred coin it spends more than the other")
    fraud_detect_pct: int = rule(20, 0, 100, S, "Chance that a vote bent by fraud is found out, at full fraud (%)")
    opinion_weight_pct: int = rule(30, 0, 100, S, "How far the people's opinion of what is asked moves the vote toward yes or no (%)")
    media_shift: int = rule(5, 0, 100, S, "Points of support an outlet of the realm gives the side its owner backs, at full reach")
    speech_shift: int = rule(5, 0, 100, S, "Points of support a speech of the season gives the side its speaker backs, at full effect")
    fraud_shift_pct: int = rule(50, 0, 100, S, "Share of the fraud that is added to the side that bends the vote (%)")
    assembly_call_pct: int = rule(5, 0, 100, S, "Chance in an epoch that a realm ruled by an assembly puts an open question to its people (%)")
    obey_chance_pct: int = rule(60, 0, 100, S, "Chance a ruler acts on a vote that did not bind them (%)")
    fraud_step: int = rule(20, 0, 100, S, "Fraud one who bends a vote adds")
    salience_turnout_pct: int = rule(60, 0, 100, S, "Turnout of those allowed to vote on a question that touches them most (%)")
