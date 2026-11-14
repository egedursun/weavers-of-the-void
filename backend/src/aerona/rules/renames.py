from collections.abc import Mapping
from types import MappingProxyType

from aerona.domain.enums.cosmography import GalaxyType
from aerona.domain.enums.economy import CommodityKind
from aerona.rules.registry.war_depth import RENAMED_RULES as WAR_RENAMES

RuleKey = tuple[str, str]

RENAMED_RULES: Mapping[RuleKey, RuleKey] = MappingProxyType(
    {
        **{("economy", f"consumption_{kind.value}_per_1000"): ("consumption", f"{kind.value}_per_1000") for kind in CommodityKind},
        **WAR_RENAMES,
        **{("galaxy_types", f"{kind.value}_arms"): ("galaxy_types", f"{kind.value}_arms_max") for kind in GalaxyType},
        ("mobilisation", "martial_pct"): ("levies", "martial_pct"),
        ("star_life", "main_epochs"): ("stellar_evolution", "sun_life_epochs"),
        ("mobilisation", "cohesion_pct"): ("levies", "cohesion_pct"),
        ("mobilisation", "harvest_pct"): ("levies", "harvest_pct"),
        ("son_tools", "stitch_per_epoch"): ("son_tools", "seal_per_epoch"),
        ("son_tools", "stitch_cost"): ("son_tools", "seal_cost"),
        ("son_tools", "stitch_ap"): ("son_tools", "seal_ap"),
        ("son_tools", "stitch_leak_reduction"): ("son_tools", "seal_leak_reduction"),
        ("creatures", "chimera_weave_chance"): ("creatures", "chimera_merge_chance"),
        ("creatures", "chimera_weave_distance"): ("creatures", "chimera_merge_distance"),
        ("beyond", "restitch_route_cost"): ("beyond", "reopen_route_cost"),
        ("rarity_gates", "stitch_leak"): ("rarity_gates", "seal_leak"),
        ("oaths", "brotherhood_chance"): ("oaths", "kinship_chance"),
        ("guild_ranks", "journeyman_at"): ("guild_ranks", "fellow_at"),
        ("setup_wizard", "darkness"): ("setup_wizard", "danger"),
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
