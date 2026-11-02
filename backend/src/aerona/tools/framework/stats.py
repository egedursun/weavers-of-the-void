from typing import Any

from pydantic import TypeAdapter

from aerona.catalog.entity_types import EntityTypeSpec
from aerona.core.random import SeededRandom
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import EntityStats
from aerona.rules.registry import Rules

PERCENT = 100
POPULATION_KEY = "population"
FOLLOWERS_KEY = "followers"
AGE_KEY = "age"
LIFESPAN_KEY = "lifespan"
HP_KEY = "hp"
LIVING_HP_TYPES = frozenset({EntityType.MORTAL, EntityType.SPECIES})
STATS_ADAPTER: TypeAdapter[EntityStats] = TypeAdapter(EntityStats)


def band_ceiling(rules: Rules, key: str, high: int | None, power: int) -> int | None:
    tools = rules.son_tools
    if tools.stat_band <= 0:
        return high
    if high is not None and high <= PERCENT:
        default = _clamp(tools.default_stat_base + max(1, power) * tools.default_stat_per_power, 0, PERCENT)
        return min(high, default + tools.stat_band)
    if key == HP_KEY:
        ceiling = round((tools.hp_base + max(1, power) * tools.hp_per_power) * tools.large_stat_band_pct / PERCENT)
        return min(high, ceiling) if high is not None else ceiling
    return high


def fill_stats(rules: Rules, spec: EntityTypeSpec, given: dict[str, Any], power: int, *, banded: bool = True) -> dict[str, int]:
    tools = rules.son_tools
    filled: dict[str, int] = {}
    for field in spec.stats:
        low, high = field.bounds(rules)
        value = given.get(field.key)
        if isinstance(value, (int, float)):
            ceiling = band_ceiling(rules, field.key, high, power) if banded else high
            filled[field.key] = _clamp(round(value), low, ceiling)
        elif field.key == HP_KEY and spec.type in LIVING_HP_TYPES:
            filled[field.key] = _clamp(max(tools.hp_minimum, tools.hp_base + max(1, power) * tools.hp_per_power), low, high)
        elif high is not None and high <= PERCENT:
            filled[field.key] = _clamp(tools.default_stat_base + power * tools.default_stat_per_power, low, high)
        elif field.key == AGE_KEY:
            filled[field.key] = tools.default_mortal_age
        elif field.key == LIFESPAN_KEY:
            filled[field.key] = tools.default_mortal_lifespan
        elif field.key == POPULATION_KEY:
            factor = tools.people_population_per_power_sq if spec.type is EntityType.PEOPLE else tools.other_population_per_power_sq
            filled[field.key] = _clamp(factor * power * power, low, high)
        elif field.key == FOLLOWERS_KEY:
            filled[field.key] = _clamp(tools.cult_followers_per_power_sq * power * power, low, high)
        else:
            filled[field.key] = low
    return filled


def _clamp(value: float, low: int, high: int | None) -> int:
    bounded = max(low, round(value))
    return bounded if high is None else min(high, bounded)


def mortal_age(rules: Rules, stats: dict[str, int], rng: SeededRandom) -> dict[str, int]:
    lifespan = stats.get(LIFESPAN_KEY, 0)
    if lifespan <= 0:
        return stats
    tools = rules.son_tools
    low_pct, high_pct = sorted((tools.mortal_age_min_pct, tools.mortal_age_max_pct))
    youngest = round(lifespan * low_pct / PERCENT)
    oldest = max(youngest, round(lifespan * high_pct / PERCENT))
    age = stats.get(AGE_KEY)
    if age is None or not youngest <= age <= oldest:
        stats = {**stats, AGE_KEY: youngest + rng.integer(0, oldest - youngest)}
    return stats


def stats_model(spec: EntityTypeSpec, values: dict[str, int]) -> EntityStats:
    return STATS_ADAPTER.validate_python({"kind": spec.type.value, **values})
