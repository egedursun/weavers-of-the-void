from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.constants.engine import UNBOUNDED_STAT
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityType
from aerona.engine.primitives.numbers import round_half_up
from aerona.rules.registry import Rules

POPULATION_KEY = "population"
FOLLOWERS_KEY = "followers"


def has_stat(entity: EntityRow, key: str) -> bool:
    return key in type(entity.stats).model_fields


def stat(entity: EntityRow, key: str) -> int | None:
    if not has_stat(entity, key):
        return None
    value = getattr(entity.stats, key)
    return value if isinstance(value, int) else None


def stat_or(entity: EntityRow, key: str, default: int) -> int:
    value = stat(entity, key)
    return default if value is None else value


def set_stats(entity: EntityRow, **values: int | None) -> bool:
    update = {key: value for key, value in values.items() if has_stat(entity, key) and getattr(entity.stats, key) != value}
    if not update:
        return False
    entity.stats = entity.stats.model_copy(update=update)
    return True


def headcount_key(entity: EntityRow) -> str:
    return FOLLOWERS_KEY if entity.entity_type is EntityType.CULT else POPULATION_KEY


def headcount_value(entity: EntityRow) -> int | None:
    return stat(entity, headcount_key(entity))


def headcount(entity: EntityRow) -> int:
    return stat_or(entity, headcount_key(entity), 0)


def headcount_bounds(rules: Rules, entity: EntityRow) -> tuple[int, int]:
    limits = rules.limits
    if entity.entity_type is EntityType.CULT:
        return 1, limits.cult_follower_cap
    if entity.entity_type is EntityType.PEOPLE:
        return limits.people_population_floor, limits.people_population_cap
    return limits.population_floor, limits.settlement_population_cap


def shift_stat(entity: EntityRow, key: str, delta: float, default: int | None = None, *, low: int = 0, high: int = PERCENT) -> int | None:
    current = stat(entity, key)
    if current is None:
        if default is None or not has_stat(entity, key):
            return None
        current = default
    updated = max(low, min(high, round_half_up(current + delta)))
    set_stats(entity, **{key: updated})
    return updated


def stat_bounds(rules: Rules, entity: EntityRow, key: str) -> tuple[int, int]:
    spec = ENTITY_TYPES[entity.entity_type].stat(key)
    if spec is None:
        return 0, UNBOUNDED_STAT
    low, high = spec.bounds(rules)
    return low, UNBOUNDED_STAT if high is None else high


def put_stat(rules: Rules, entity: EntityRow, key: str, value: float) -> int | None:
    if not has_stat(entity, key):
        return None
    low, high = stat_bounds(rules, entity, key)
    bounded = max(low, min(high, round_half_up(value)))
    set_stats(entity, **{key: bounded})
    return bounded


def _current(entity: EntityRow, key: str, default: int | None) -> int | None:
    current = stat(entity, key)
    if current is None and default is not None and has_stat(entity, key):
        return default
    return current


def shift_bounded(rules: Rules, entity: EntityRow, key: str, delta: float, default: int | None = None) -> int | None:
    current = _current(entity, key, default)
    return None if current is None else put_stat(rules, entity, key, current + delta)


def scale_stat(rules: Rules, entity: EntityRow, key: str, factor: float, default: int | None = None) -> int | None:
    current = _current(entity, key, default)
    return None if current is None else put_stat(rules, entity, key, current * factor)
