from collections.abc import Mapping
from types import MappingProxyType

from aerona.domain.enums.economy import CommodityKind
from aerona.rules.registry.war_depth import RENAMED_RULES as WAR_RENAMES

RuleKey = tuple[str, str]

RENAMED_RULES: Mapping[RuleKey, RuleKey] = MappingProxyType(
    {
        **{("economy", f"consumption_{kind.value}_per_1000"): ("consumption", f"{kind.value}_per_1000") for kind in CommodityKind},
        **WAR_RENAMES,
        ("mobilisation", "martial_pct"): ("levies", "martial_pct"),
        ("mobilisation", "cohesion_pct"): ("levies", "cohesion_pct"),
        ("mobilisation", "harvest_pct"): ("levies", "harvest_pct"),
    }
)


def canonical_key(namespace: str, key: str) -> RuleKey:
    return RENAMED_RULES.get((namespace, key), (namespace, key))


def canonical_overrides(overrides: Mapping[RuleKey, float]) -> dict[RuleKey, float]:
    renamed = {canonical_key(*item): value for item, value in overrides.items() if item in RENAMED_RULES}
    return {**renamed, **{item: value for item, value in overrides.items() if item not in RENAMED_RULES}}
