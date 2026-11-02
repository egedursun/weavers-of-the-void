from dataclasses import dataclass

RARITY_KEYS = ("common", "uncommon", "rare", "epic", "legendary", "mythic")


@dataclass(frozen=True)
class AscendingChain:
    paths: tuple[str, ...]
    strict: bool = False


ASCENDING_CHAINS: list[AscendingChain] = [
    AscendingChain(
        ("core_rules.tier_uncommon", "core_rules.tier_rare", "core_rules.tier_epic", "core_rules.tier_legendary", "core_rules.tier_mythic"), strict=True
    ),
    AscendingChain(("core_rules.relation_cold", "core_rules.relation_enemy", "core_rules.relation_blood_enemy"), strict=True),
    AscendingChain(("core_rules.relation_friend", "core_rules.relation_close_friend", "core_rules.relation_sibling"), strict=True),
    *(AscendingChain((f"rarities.{rarity}_stat_min", f"rarities.{rarity}_stat_max")) for rarity in RARITY_KEYS),
    AscendingChain(("diplomacy.grudge_threshold", "diplomacy.peace_threshold", "diplomacy.alliance_threshold"), strict=True),
    AscendingChain(("campaigns.army_power_min", "campaigns.army_power_max")),
    AscendingChain(("campaigns.war_power_min", "campaigns.war_power_max")),
    AscendingChain(("campaigns.battle_event_power_min", "campaigns.battle_event_power_max")),
    AscendingChain(("campaigns.breach_min_pct", "campaigns.breach_max_pct")),
    AscendingChain(("society.food_rate_min_pct", "society.food_rate_max_pct")),
    AscendingChain(("society.price_min_pct", "society.price_max_pct")),
    AscendingChain(("society.price_min_pct", "society.price_food_max_pct")),
    AscendingChain(("society.price_scarcity_food", "society.price_plenty_food")),
    AscendingChain(("society.poverty_revolt_min_population", "society.poverty_revolt_always_population")),
    AscendingChain(("heroes.quest_success_min_pct", "heroes.quest_success_max_pct")),
    AscendingChain(("heroes.birth_min_population", "heroes.birth_always_population")),
    AscendingChain(("religion.schism_min_followers", "religion.schism_always_followers")),
    AscendingChain(("knowledge.dark_age_forget_protected_chance", "knowledge.dark_age_forget_chance")),
    AscendingChain(("disasters.city_plague_crowd_floor", "disasters.city_plague_always_population")),
    AscendingChain(("cosmic_horror.madness_threshold", "cosmic_horror.clouding_threshold"), strict=True),
    AscendingChain(("cosmic_horror.son_madness_threshold", "cosmic_horror.son_clouding_threshold"), strict=True),
    AscendingChain(("cosmic_horror.warning_1", "cosmic_horror.warning_2", "cosmic_horror.outer_being_threshold"), strict=True),
    AscendingChain(("travel.route_danger_min", "travel.route_danger_max")),
    AscendingChain(("world_birth.regions_min", "world_birth.regions_max")),
    AscendingChain(("world_birth.words_min", "world_birth.words_max")),
    AscendingChain(("world_physics.time_factor_min", "world_physics.time_factor_max")),
    AscendingChain(("civilization.city_state_population", "civilization.kingdom_population")),
    AscendingChain(("civilization.interstellar_worlds", "civilization.cosmic_worlds")),
    AscendingChain(("sky.alignment_danger_floor", "sky.alignment_danger_cap")),
]
