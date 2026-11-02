from collections.abc import Mapping

from pydantic import TypeAdapter

from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import EntityStats
from aerona.rules.registry import Rules

STATS_ADAPTER: TypeAdapter[EntityStats] = TypeAdapter(EntityStats)


def stats_from(entity_type: EntityType, values: Mapping[str, float | int | None], rules: Rules) -> EntityStats:
    spec = ENTITY_TYPES[entity_type]
    cleaned: dict[str, object] = {"kind": entity_type.value}
    for key, raw in values.items():
        field = spec.stat(key)
        if field is None or raw is None:
            continue
        low, high = field.bounds(rules)
        value = round(float(raw))
        cleaned[key] = max(low, value if high is None else min(high, value))
    return STATS_ADAPTER.validate_python(cleaned)
