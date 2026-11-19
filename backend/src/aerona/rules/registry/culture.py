from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class CultureRules:
    first_loanword_pct: int = rule(80, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Loanword on first contact (%)")
    trade_loanword_pct: int = rule(50, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Loanword in trade contact (%)")
    first_tradition_pct: int = rule(50, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Tradition transfer on first contact (%)")
    trade_tradition_pct: int = rule(25, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Tradition transfer in trade contact (%)")
    first_knowledge_pct: int = rule(40, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Knowledge transfer on first contact (%)")
    trade_knowledge_pct: int = rule(10, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Knowledge transfer in trade contact (%)")
    first_god_pct: int = rule(30, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "God transfer on first contact (%)")
    trade_god_pct: int = rule(6, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "God transfer in trade contact (%)")
    exchange_cap: int = rule(2, 0, 10000, RuleGroup.RELIGION_AND_LANGUAGE, "Maximum cultural exchanges per epoch, before the communities are counted")
    exchange_communities_per_extra: int = rule(
        10, 0, 100000, RuleGroup.RELIGION_AND_LANGUAGE, "One more cultural exchange per epoch for every this many communities (0 none)"
    )
    exchange_chance: int = rule(12, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Cultural exchange along a trade route (%)")
    exchange_direction_pct: int = rule(50, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Trade-route exchange: chance the bond source influences its partner (%)")
