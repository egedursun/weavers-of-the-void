from collections.abc import Mapping
from types import MappingProxyType

from aerona.domain.enums.economy import CommodityKind

RuleKey = tuple[str, str]

RENAMED_RULES: Mapping[RuleKey, RuleKey] = MappingProxyType(
    {
        **{("economy", f"consumption_{kind.value}_per_1000"): ("consumption", f"{kind.value}_per_1000") for kind in CommodityKind},
        ("peoples", "levy_martial_pct"): ("mobilisation", "martial_pct"),
        ("peoples", "levy_cohesion_pct"): ("mobilisation", "cohesion_pct"),
        ("peoples", "harvest_levy_pct"): ("mobilisation", "harvest_pct"),
    }
)


def canonical_key(namespace: str, key: str) -> RuleKey:
    return RENAMED_RULES.get((namespace, key), (namespace, key))


def canonical_overrides(overrides: Mapping[RuleKey, float]) -> dict[RuleKey, float]:
    renamed = {canonical_key(*item): value for item, value in overrides.items() if item in RENAMED_RULES}
    return {**renamed, **{item: value for item, value in overrides.items() if item not in RENAMED_RULES}}
