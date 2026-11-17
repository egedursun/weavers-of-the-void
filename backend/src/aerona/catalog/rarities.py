from dataclasses import dataclass

from aerona.constants.tool_inputs import POWER_LEVEL_MIN
from aerona.domain.enums.rarity import RARITY_ORDER, Rarity
from aerona.domain.models.names import NameSimilarityPolicy
from aerona.rules.registry import Rules

RARITY_LABELS: dict[Rarity, str] = {
    Rarity.COMMON: "Common",
    Rarity.UNCOMMON: "Uncommon",
    Rarity.RARE: "Rare",
    Rarity.EPIC: "Epic",
    Rarity.LEGENDARY: "Legendary",
    Rarity.MYTHIC: "Mythic",
}

DEFAULT_FIRST_SONS = (Rarity.COMMON, Rarity.RARE, Rarity.LEGENDARY)
SUMMONABLE_RARITIES = frozenset(rarity for rarity in RARITY_ORDER if rarity is not Rarity.MYTHIC)


@dataclass(frozen=True)
class RarityProfile:
    rarity: Rarity
    label: str
    action_points: int
    essence_regen: int
    stat_min: int
    stat_max: int
    power_cap: int
    max_turns: int
    summon_weight: int

    @property
    def rank(self) -> int:
        return self.rarity.rank

    @property
    def summonable(self) -> bool:
        return self.rarity in SUMMONABLE_RARITIES and self.summon_weight > 0


def build_rarity_table(rules: Rules) -> dict[Rarity, RarityProfile]:
    table = rules.rarities
    rows = {
        Rarity.COMMON: (
            table.common_action_points,
            table.common_essence_regen,
            table.common_stat_min,
            table.common_stat_max,
            table.common_power_cap,
            table.common_max_turns,
            table.common_summon_weight,
        ),
        Rarity.UNCOMMON: (
            table.uncommon_action_points,
            table.uncommon_essence_regen,
            table.uncommon_stat_min,
            table.uncommon_stat_max,
            table.uncommon_power_cap,
            table.uncommon_max_turns,
            table.uncommon_summon_weight,
        ),
        Rarity.RARE: (
            table.rare_action_points,
            table.rare_essence_regen,
            table.rare_stat_min,
            table.rare_stat_max,
            table.rare_power_cap,
            table.rare_max_turns,
            table.rare_summon_weight,
        ),
        Rarity.EPIC: (
            table.epic_action_points,
            table.epic_essence_regen,
            table.epic_stat_min,
            table.epic_stat_max,
            table.epic_power_cap,
            table.epic_max_turns,
            table.epic_summon_weight,
        ),
        Rarity.LEGENDARY: (
            table.legendary_action_points,
            table.legendary_essence_regen,
            table.legendary_stat_min,
            table.legendary_stat_max,
            table.legendary_power_cap,
            table.legendary_max_turns,
            table.legendary_summon_weight,
        ),
    }
    profiles = {
        rarity: RarityProfile(rarity, RARITY_LABELS[rarity], ap, regen, low, high, cap, turns, weight)
        for rarity, (ap, regen, low, high, cap, turns, weight) in rows.items()
    }
    profiles[Rarity.MYTHIC] = RarityProfile(
        Rarity.MYTHIC,
        RARITY_LABELS[Rarity.MYTHIC],
        table.mythic_action_points,
        table.mythic_essence_regen,
        table.mythic_stat_min,
        table.mythic_stat_max,
        table.mythic_power_cap,
        table.mythic_max_turns,
        0,
    )
    return profiles


def _entity_tiers(rules: Rules) -> tuple[tuple[int, Rarity], ...]:
    core = rules.core_rules
    return (
        (core.tier_mythic, Rarity.MYTHIC),
        (core.tier_legendary, Rarity.LEGENDARY),
        (core.tier_epic, Rarity.EPIC),
        (core.tier_rare, Rarity.RARE),
        (core.tier_uncommon, Rarity.UNCOMMON),
    )


def entity_rarity(rules: Rules, power_level: int) -> Rarity:
    return next((rarity for threshold, rarity in _entity_tiers(rules) if power_level >= threshold), Rarity.COMMON)


def entity_power_band(rules: Rules, rarity: Rarity) -> tuple[int, int | None]:
    tiers = _entity_tiers(rules)
    low = next((threshold for threshold, tier in tiers if tier is rarity), POWER_LEVEL_MIN)
    higher = [threshold for threshold, tier in tiers if tier.rank > rarity.rank]
    return low, (min(higher) - 1 if higher else None)


def name_similarity_policy(rules: Rules) -> NameSimilarityPolicy:
    language = rules.language
    return NameSimilarityPolicy(
        similar_max_length=language.similar_name_max_length,
        family_cap=language.name_family_cap,
        root_letters=language.root_letters,
    )
