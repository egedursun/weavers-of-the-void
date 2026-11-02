from dataclasses import dataclass, field
from typing import Any, get_args

from pydantic import BaseModel, TypeAdapter, ValidationError

from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import EntityStats
from aerona.migration.legacy.values import as_dict, as_int
from aerona.migration.legacy.vocabulary import Vocabulary

STATS_ADAPTER: TypeAdapter[EntityStats] = TypeAdapter(EntityStats)
KIND = "kind"
CLAMPS: tuple[tuple[int, int | None], ...] = ((0, 100), (1, 10), (0, None))


def _models() -> dict[str, type[BaseModel]]:
    union = get_args(EntityStats)[0]
    return {model.model_fields[KIND].default: model for model in get_args(union)}


STAT_MODELS = _models()


@dataclass
class StatReading:
    stats: EntityStats
    extras: dict[str, int] = field(default_factory=dict)
    dropped: list[str] = field(default_factory=list)
    clamped: list[str] = field(default_factory=list)


def _accepts(model: type[BaseModel], name: str, value: int) -> bool:
    try:
        model.model_validate({name: value})
    except ValidationError:
        return False
    return True


def _fit(model: type[BaseModel], name: str, value: int) -> int | None:
    if _accepts(model, name, value):
        return value
    for low, high in CLAMPS:
        candidate = max(low, value) if high is None else max(low, min(high, value))
        if _accepts(model, name, candidate):
            return candidate
    return None


def read_stats(vocabulary: Vocabulary, entity_type: EntityType, payload: Any) -> StatReading:
    mapping = vocabulary.entity_stats.get(entity_type.value, {})
    model = STAT_MODELS[entity_type.value]
    values: dict[str, int] = {}
    reading = StatReading(stats=STATS_ADAPTER.validate_python({KIND: entity_type.value}))
    for key, raw in as_dict(payload).items():
        number = as_int(raw)
        english = mapping.get(key)
        extra = vocabulary.entity_extra_stats.get(key)
        if number is None:
            reading.dropped.append(f"{entity_type.value}.{key}")
        elif english is not None:
            fitted = _fit(model, english, number)
            if fitted is None:
                reading.dropped.append(f"{entity_type.value}.{key}")
            else:
                if fitted != number:
                    reading.clamped.append(f"{english} {number} -> {fitted}")
                values[english] = fitted
        elif extra is not None:
            reading.extras[extra] = number
        else:
            reading.dropped.append(f"{entity_type.value}.{key}")
    reading.stats = STATS_ADAPTER.validate_python({KIND: entity_type.value, **values})
    return reading
