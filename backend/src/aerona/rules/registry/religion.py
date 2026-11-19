from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class ReligionRules:
    conversion_cap: int = rule(1, 0, 1000, RuleGroup.RELIGION_AND_LANGUAGE, "Maximum communities changing religion per epoch (base)")
    conversion_cap_community_divisor: int = rule(
        10, 0, 100000, RuleGroup.RELIGION_AND_LANGUAGE, "Religious conversion and syncretism caps grow by 1 for every this many communities (0: fixed)"
    )
    seeker_pull_chance: int = rule(12, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "A god-seeking community converts to its neighbour's god (%)")
    conversion_chance_cap: int = rule(30, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Cap of a religious conversion chance (%)")
    dominant_god_threshold_pct: int = rule(
        30,
        0,
        100,
        RuleGroup.RELIGION_AND_LANGUAGE,
        "Dominant god: if more than this percentage of worshipping communities are with one god, the chance of converting to it decreases as its share grows (reaching zero as its share approaches 100%)",
    )
    syncretism_pct: int = rule(40, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Share of religious conversions that are syncretic (%)")
    preach_base_pct: int = rule(2, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Base of conversion by cult preaching (%)")
    preach_influence_divisor: int = rule(800, 1, 100000, RuleGroup.RELIGION_AND_LANGUAGE, "Preaching chance: cult influence / this number")
    preach_follower_max_pct: int = rule(8, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Maximum contribution of followers to the preaching chance (%)")
    preach_follower_min_divisor: int = rule(500, 1, 1000000, RuleGroup.RELIGION_AND_LANGUAGE, "Preaching chance: followers / at least this number")
    preach_population_mult: int = rule(4, 1, 1000, RuleGroup.RELIGION_AND_LANGUAGE, "Preaching chance: followers / (population \u00d7 this number)")
    conversion_renown_divisor: int = rule(1500, 1, 1000000, RuleGroup.RELIGION_AND_LANGUAGE, "Conversion: renown difference between gods / this number")
    conversion_seeker_bonus_pct: int = rule(10, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Contribution of a god-seeking community to conversion (%)")
    schism_cap: int = rule(1, 0, 1000, RuleGroup.RELIGION_AND_LANGUAGE, "Maximum cult schisms per epoch (base)")
    schism_cap_cult_divisor: int = rule(10, 0, 100000, RuleGroup.RELIGION_AND_LANGUAGE, "Cult schism cap grows by 1 for every this many cults (0: fixed)")
    schism_top_pct: int = rule(50, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Cults that can split: the world's top X% most populous")
    schism_always_followers: int = rule(3000, 0, 10000000, RuleGroup.RELIGION_AND_LANGUAGE, "A cult with this many followers can always split")
    schism_min_age: int = rule(2, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Minimum age of a cult that can split (epochs)")
    schism_large_min_age: int = rule(4, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Minimum age for a non-zealous cult to split (epochs)")
    schism_zealotry_gain: int = rule(10, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Zealotry gain of the breakaway sect")
    schism_influence_loss: int = rule(10, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Influence deficit of the breakaway sect")
    schism_patron_relation: int = rule(10, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Relation loss between old and new patron in a schism")
    schism_zealous_chance: int = rule(22, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "A zealous cult splits (%)")
    schism_large_chance: int = rule(10, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "A large and old cult splits over doctrinal dispute (%)")
    schism_zealotry: int = rule(60, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Zealotry of a cult counted as zealous")
    schism_min_followers: int = rule(400, 0, 1000000, RuleGroup.RELIGION_AND_LANGUAGE, "Minimum followers of a cult that can split")
    schism_large_followers: int = rule(800, 0, 1000000, RuleGroup.RELIGION_AND_LANGUAGE, "Followers needed for a non-zealous cult to split")
    schism_split_pct: int = rule(30, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Share of followers leaving in a split (%)")
    godlessness_piety: int = rule(35, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "A community below this piety may become godless")
    godlessness_chance: int = rule(15, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "A community with weak faith becomes godless (%)")
    syncretism_cap: int = rule(1, 0, 1000, RuleGroup.RELIGION_AND_LANGUAGE, "Maximum communities adding a syncretic secondary god per epoch (base)")
    reverence_weight_pct: int = rule(
        50, 0, 100, RuleGroup.RELIGION_AND_LANGUAGE, "Weight of a syncretic secondary reverence compared with worship when counting a god's share (%)"
    )
