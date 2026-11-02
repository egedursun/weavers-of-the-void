from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class EssenceRules:
    overflow_pct: int = rule(8, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Share of essence above the cap overflowing into the world each epoch (%)")
    overflow_per_fertility: int = rule(
        10,
        1,
        1000,
        RuleGroup.CREATOR_AND_ESSENCE,
        "Every this much overflowing essence gives regions 1 fertility in total (shared starting from the most barren region)",
    )
    overflow_fertility_cap: int = rule(70, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Overflowing essence does not raise a region's fertility above this")
    godless_gnaw: int = rule(3, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Essence gnawed by each godless community per epoch")
    renown_keep_pct: int = rule(95, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Share of a son's renown kept each epoch (%)")
    over_cap_income_pct: int = rule(
        50,
        0,
        100,
        RuleGroup.CREATOR_AND_ESSENCE,
        "Share of the Creator's epoch income remaining while above the essence cap (BALANCE.creator_essence_soft_cap) (%)",
    )
    exile_regen_pct: int = rule(0, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Ratio of an exiled son's per-epoch essence regeneration to normal regeneration (%)")
    over_cap_decline_pct: int = rule(
        100,
        0,
        100,
        RuleGroup.CREATOR_AND_ESSENCE,
        "Above the cap the income also shrinks with the essence's ratio to the cap (%; 100: half at twice the cap, a third at three times; 0 off)",
    )
    overflow_sons_pct: int = rule(
        15,
        0,
        100,
        RuleGroup.CREATOR_AND_ESSENCE,
        "Share of the overflowing essence that flows to the poorest sons who are not rebels (%; the rest blesses the land)",
    )
    overflow_sons_fill_pct: int = rule(50, 0, 100, RuleGroup.CREATOR_AND_ESSENCE, "Overflowing essence fills a son at most to this share of his essence cap")
