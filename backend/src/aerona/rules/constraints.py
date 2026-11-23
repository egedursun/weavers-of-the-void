from dataclasses import dataclass

from aerona.domain.enums.cosmography import GalaxyType
from aerona.domain.enums.meta import ACHIEVEMENT_TIERS, AchievementKey

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
    AscendingChain(("markets.price_floor_pct", "markets.price_cap_pct")),
    AscendingChain(("market.debt_patience_years", "market.debt_expiry_years"), strict=True),
    AscendingChain(("economy.supply_index_epoch", "economy.storage_base_index")),
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
    *(AscendingChain((f"galaxy_types.{kind.value}_arms_min", f"galaxy_types.{kind.value}_arms_max")) for kind in GalaxyType),
    AscendingChain(("world_birth.regions_min", "world_birth.regions_max")),
    AscendingChain(("world_birth.words_min", "world_birth.words_max")),
    AscendingChain(("world_physics.time_factor_min", "world_physics.time_factor_max")),
    AscendingChain(("civilization.city_state_population", "civilization.realm_population")),
    AscendingChain(("civilization.interstellar_worlds", "civilization.cosmic_worlds")),
    AscendingChain(("sky.alignment_danger_floor", "sky.alignment_danger_cap")),
    AscendingChain(
        ("environment.frozen_below", "environment.cold_below", "environment.temperate_below", "environment.warm_below", "environment.hot_below"), strict=True
    ),
    AscendingChain(("weather.cold_threshold", "weather.hot_threshold"), strict=True),
    AscendingChain(
        (
            "seasons.two_seasons_below_tilt",
            "seasons.three_seasons_below_tilt",
            "seasons.four_seasons_below_tilt",
            "seasons.five_seasons_below_tilt",
            "seasons.six_seasons_below_tilt",
            "seasons.seven_seasons_below_tilt",
        ),
        strict=True,
    ),
    AscendingChain(("seasons.tilt_min", "seasons.tilt_roll_max", "seasons.tilt_max")),
    AscendingChain(("long_seasons.eruption_years_min", "long_seasons.eruption_years_max")),
    AscendingChain(("long_seasons.eruption_strength_min", "long_seasons.eruption_world_strength")),
    AscendingChain(("seasons.seven_seasons_below_tilt", "seasons.tilt_max")),
    AscendingChain(("seasons.year_days_min", "seasons.year_days_base", "seasons.year_days_max")),
    AscendingChain(("seasons.day_hours_min", "seasons.day_hours_max")),
    AscendingChain(("harvest.famine_event_below", "harvest.notable_threshold"), strict=True),
    AscendingChain(("land_use.exhausted_soil_below", "harvest.normal_soil"), strict=True),
    AscendingChain(("injury.severity_spread_low_pct", "injury.severity_spread_high_pct"), strict=True),
    AscendingChain(("injury.cut_deep_at", "injury.cut_sever_small_at", "injury.cut_sever_at")),
    AscendingChain(("injury.pierce_gouge_at", "injury.pierce_destroy_at"), strict=True),
    AscendingChain(("injury.blunt_fracture_at", "injury.blunt_crush_at"), strict=True),
    AscendingChain(("healing.herbs_level", "healing.surgery_level", "healing.prosthetics_level"), strict=True),
    AscendingChain(("healing.prosthetics_level", "healing.magic_reattachment_level", "healing.reattachment_level")),
    AscendingChain(("healing.herbs_infection_cut_pct", "healing.surgery_infection_cut_pct")),
    AscendingChain(("capacities.fertility_start_pct", "capacities.fertility_prime_end_pct", "capacities.fertility_end_pct"), strict=True),
    AscendingChain(("conditions.void_taint_sanity", "conditions.madness_sanity", "conditions.madness_recover_sanity"), strict=True),
    AscendingChain(("traits.birth_min", "traits.birth_max", "traits.max_traits")),
    AscendingChain(("memory.forget_below", "memory.vengeance_threshold"), strict=True),
    AscendingChain(("opinion.reading_floor_pct", "opinion.reading_ceiling_pct"), strict=True),
    AscendingChain(("skills.rust_floor_pct", "skills.decline_start_pct")),
    AscendingChain(("achievements.tier_2_points_pct", "achievements.tier_3_points_pct")),
    *(AscendingChain(tuple(f"achievements.tier_{tier}_{key.value}" for tier in ACHIEVEMENT_TIERS), strict=True) for key in AchievementKey),
]
