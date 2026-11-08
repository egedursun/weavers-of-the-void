from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

K = RuleGroup.CIVILIZATION


@dataclass(frozen=True)
class ResearchDepthRules:
    options: int = rule(3, 1, 12, K, "Techniques a researching holder draws to choose among each epoch")
    focus_pct: int = rule(100, 0, 400, K, "Progress the chosen technique makes each epoch, as a share of the base pace (%)")
    unfocused_pct: int = rule(25, 0, 100, K, "Progress every other open technique makes each epoch, as a share of the base pace (%)")
    need_weight: int = rule(3, 1, 20, K, "How much more often a technique of a branch the holder needs is drawn")
    boost_weight: int = rule(2, 1, 20, K, "How much more often a technique already pushed by a deed is drawn")
    boost_progress: int = rule(35, 0, 100, K, "Progress a fitting deed adds to a technique")
    fishing_scale: int = rule(40, 0, 100000, K, "Fish a community must land in an epoch to push sailing and charts")
    great_trial_evidence: int = rule(60, 0, 100, K, "Evidence a closed trial needs to count as a great trial")
    great_debt: int = rule(400, 0, 1000000, K, "Principal a loan needs to count as a great debt")
    catch_up_pct: int = rule(10, 0, 100, K, "Faster a technique is learned for each neighbour that knows it (%)")
    catch_up_cap: int = rule(50, 0, 300, K, "Most a technique can be sped up by neighbours who know it (%)")
    refugee_leak: int = rule(8, 0, 99, K, "Progress toward each technique of their homeland that refugees bring to the place that shelters them")
    library_leak: int = rule(10, 0, 99, K, "Progress toward each technique kept in a conquered library that its occupier gains each epoch")
    captive_leak: int = rule(5, 0, 100, K, "Progress a captor makes on a technique its captives' people know")
    origin_wealth: int = rule(60, 0, 100, K, "Prosperity a community needs to give birth to an institution")
    origin_trade: int = rule(2, 0, 50, K, "Trade partners a community needs to give birth to an institution")
    spread_pct: int = rule(12, 0, 100, K, "Chance an institution spreads to a bordering or trading community each epoch (%)")
    kin_spread_pct: int = rule(50, 0, 300, K, "Extra spread chance to a community of the same people or faith (%)")
    embrace_cost: int = rule(40, 0, 10000, K, "Treasury a realm spends to embrace an institution that reached it")
    embrace_pct: int = rule(10, 0, 100, K, "Faster research for each embraced institution (%)")
    refusal_pct: int = rule(3, 0, 100, K, "Slower research for each epoch an institution that reached a community is left unembraced (%)")
    refusal_cap: int = rule(45, 0, 100, K, "Most research can be slowed by unembraced institutions (%)")
    patron_research_pct: int = rule(20, 0, 300, K, "Faster research of a realm whose court scholar is funded, at full skill (%)")
    patron_prestige: int = rule(2, 0, 100, K, "Prestige a ruler gains each epoch from funding a court scholar")
    patron_stipend: int = rule(8, 0, 10000, K, "Treasury a court scholar's stipend costs each epoch")
    agreement_share_pct: int = rule(40, 0, 100, K, "Share of the gap in a branch a research agreement closes each epoch (%)")
    expertise_pct: int = rule(60, 0, 300, K, "Weight of a scholar's own field over general learning in research (%)")
    social_shift_pct: int = rule(100, 0, 300, K, "How strongly a newly adopted technique shifts values and classes (%)")
    capability_reach: int = rule(2, 0, 20, K, "Extra regions a voyage reaches with blue-water navigation")
