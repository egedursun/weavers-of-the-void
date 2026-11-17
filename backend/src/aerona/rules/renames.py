from collections.abc import Mapping
from types import MappingProxyType

from aerona.domain.enums.cosmography import GalaxyType
from aerona.domain.enums.economy import CommodityKind
from aerona.rules.registry.goals import RENAMED_RULES as GOAL_RENAMES
from aerona.rules.registry.war_depth import RENAMED_RULES as WAR_RENAMES

RuleKey = tuple[str, str]
GOLEM_RULES = (
    "min_power",
    "hp",
    "strength_base",
    "strength_die",
    "agility",
    "intelligence_base",
    "intelligence_die",
    "danger_base",
    "danger_die",
)
MERGED_RULES = (
    "default_stat",
    "die",
    "shift",
    "hp_cap",
    "trait_cap",
    "danger_bonus",
    "default_danger",
    "escape_divisor",
    "escape_population_loss_pct",
)

RENAMED_RULES: Mapping[RuleKey, RuleKey] = MappingProxyType(
    {
        **{("economy", f"consumption_{kind.value}_per_1000"): ("consumption", f"{kind.value}_per_1000") for kind in CommodityKind},
        **WAR_RENAMES,
        **GOAL_RENAMES,
        **{("galaxy_types", f"{kind.value}_arms"): ("galaxy_types", f"{kind.value}_arms_max") for kind in GalaxyType},
        ("mobilisation", "martial_pct"): ("levies", "martial_pct"),
        ("star_life", "main_epochs"): ("stellar_evolution", "sun_life_epochs"),
        ("mobilisation", "cohesion_pct"): ("levies", "cohesion_pct"),
        ("mobilisation", "harvest_pct"): ("levies", "harvest_pct"),
        ("son_tools", "stitch_per_epoch"): ("son_tools", "seal_per_epoch"),
        ("son_tools", "stitch_cost"): ("son_tools", "seal_cost"),
        ("son_tools", "stitch_ap"): ("son_tools", "seal_ap"),
        ("son_tools", "stitch_leak_reduction"): ("son_tools", "seal_leak_reduction"),
        ("creatures", "merged_weave_chance"): ("creatures", "species_merge_chance"),
        ("creatures", "merged_weave_distance"): ("creatures", "species_merge_distance"),
        ("beyond", "restitch_route_cost"): ("beyond", "reopen_route_cost"),
        ("rarity_gates", "stitch_leak"): ("rarity_gates", "seal_leak"),
        ("oaths", "brotherhood_chance"): ("oaths", "kinship_chance"),
        ("guild_ranks", "journeyman_at"): ("guild_ranks", "fellow_at"),
        ("setup_wizard", "darkness"): ("setup_wizard", "danger"),
        ("customs", "polygyny_spouses"): ("customs", "plural_first_side_spouses"),
        ("customs", "polyandry_spouses"): ("customs", "plural_second_side_spouses"),
        ("houses", "dowry_pct"): ("houses", "union_portion_pct"),
        ("households", "dowry_pct"): ("households", "union_portion_pct"),
        ("kinship_systems", "avunculocal_at"): ("kinship_systems", "first_line_kin_at"),
        ("kinship_systems", "levirate_at"): ("kinship_systems", "first_side_sibling_union_at"),
        ("kinship_systems", "sororate_at"): ("kinship_systems", "second_side_sibling_union_at"),
        ("traditions", "scar_rite_chance"): ("traditions", "body_marking_chance"),
        ("traditions", "war_dance_martial"): ("traditions", "martial_display_martial"),
        ("traditions", "ancestor_feast_placation"): ("traditions", "ancestral_rite_placation"),
        ("seasonal", "siesta_unrest"): ("seasonal", "rest_custom_unrest"),
        ("seasonal", "siesta_satisfaction"): ("seasonal", "rest_custom_satisfaction"),
        ("seasonal", "siesta_prosperity"): ("seasonal", "rest_custom_prosperity"),
        ("legitimacy", "divine_kingship"): ("legitimacy", "divine_rule"),
        ("titles", "see_followers"): ("titles", "faith_local_followers"),
        ("titles", "archsee_followers"): ("titles", "faith_high_followers"),
        ("deep_life", "role_noble_lord_charisma"): ("deep_life", "role_noble_landholder_charisma"),
        ("deep_life", "role_noble_knight_strength"): ("deep_life", "role_noble_sworn_warrior_strength"),
        ("civilization", "kingdom_population"): ("civilization", "realm_population"),
        ("civilization", "kingdom_ruled_places"): ("civilization", "realm_ruled_places"),
        ("civilization", "kingdom_knowledge"): ("civilization", "realm_knowledge"),
        ("vehicles", "kingdom_size"): ("vehicles", "realm_size"),
        ("needs", "status_knight"): ("needs", "status_sworn_warrior"),
        ("contests", "bride_romance"): ("contests", "union_romance"),
        ("belief", "return_king_claim"): ("belief", "return_ruler_claim"),
        ("belief", "return_king_usurper"): ("belief", "return_ruler_usurper"),
        ("death", "scatter_bones_cost"): ("death", "hinder_return_cost"),
        ("death", "scatter_bones_devotion_loss"): ("death", "hinder_return_devotion_loss"),
        ("death", "auto_scatter_chance"): ("death", "auto_hinder_chance"),
        ("death", "auto_scatter_relation"): ("death", "auto_hinder_relation"),
        **{("beyond", f"golem_{name}"): ("beyond", f"animated_work_{name}") for name in GOLEM_RULES},
        **{("creatures", f"chimera_{name}"): ("creatures", f"merged_{name}") for name in MERGED_RULES},
        ("creatures", "chimera_merge_chance"): ("creatures", "species_merge_chance"),
        ("creatures", "chimera_merge_distance"): ("creatures", "species_merge_distance"),
        ("prosthetics", "dragonbone"): ("prosthetics", "great_bone"),
        **{
            ("factions", f"brotherhood_{name}"): ("factions", f"order_{name}")
            for name in ("min_warrior_pct", "at_war_min_warrior_pct", "strength", "wealth", "sway")
        },
    }
)


def canonical_key(namespace: str, key: str) -> RuleKey:
    return RENAMED_RULES.get((namespace, key), (namespace, key))


def canonical_overrides(overrides: Mapping[RuleKey, float]) -> dict[RuleKey, float]:
    renamed = {canonical_key(*item): value for item, value in overrides.items() if item in RENAMED_RULES}
    return {**renamed, **{item: value for item, value in overrides.items() if item not in RENAMED_RULES}}
