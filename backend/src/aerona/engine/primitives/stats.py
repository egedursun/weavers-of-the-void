from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.constants.engine import UNBOUNDED_STAT
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityType
from aerona.engine.interconnect.guards import READ_MODE, WRITE_MODE, blocked, observed, record_flow
from aerona.engine.primitives.modifiers import LIVE_MODIFIERS, base_for, combine, live_contributions
from aerona.engine.primitives.numbers import round_half_up
from aerona.rules.registry import Rules

POPULATION_KEY = "population"
FOLLOWERS_KEY = "followers"


def has_stat(entity: EntityRow, key: str) -> bool:
    return key in type(entity.stats).model_fields


def base_stat(entity: EntityRow, key: str) -> int | None:
    if not has_stat(entity, key):
        return None
    observed(entity.entity_type.value, key, READ_MODE)
    value = getattr(entity.stats, key)
    return value if isinstance(value, int) else None


def stat(entity: EntityRow, key: str) -> int | None:
    base = base_stat(entity, key)
    if base is None:
        return None
    contributions = live_contributions(entity.id, key)
    if not contributions:
        return base
    return clamp_to_field(entity, key, combine(base, contributions).value)


def clamp_to_field(entity: EntityRow, key: str, value: float) -> int:
    live = LIVE_MODIFIERS.get()
    field = ENTITY_TYPES[entity.entity_type].stat(key)
    low, high = field.bounds(live.rules) if field is not None and live is not None else (0, None)
    bounded = max(low, round_half_up(value))
    return bounded if high is None else min(high, bounded)


def to_base(entity: EntityRow, key: str, value: int | None) -> int | None:
    if value is None:
        return None
    contributions = live_contributions(entity.id, key)
    if not contributions:
        return value
    base = base_for(contributions, value)
    current = base_stat(entity, key)
    return current if base is None else clamp_to_field(entity, key, base)


def stat_or(entity: EntityRow, key: str, default: int) -> int:
    value = stat(entity, key)
    return default if value is None else value


def set_stats(entity: EntityRow, **values: int | None) -> bool:
    based = {key: to_base(entity, key, value) for key, value in values.items() if has_stat(entity, key)}
    update = {key: value for key, value in based.items() if getattr(entity.stats, key) != value and not blocked(entity.id, key)}
    if not update:
        return False
    for key, value in update.items():
        observed(entity.entity_type.value, key, WRITE_MODE)
        before = getattr(entity.stats, key)
        if isinstance(before, int) and isinstance(value, int):
            record_flow(entity.id, key, value - before)
    entity.stats = entity.stats.model_copy(update=update)
    return True


def set_base_stats(entity: EntityRow, **values: int | None) -> bool:
    lifted: dict[str, int | None] = {}
    for key, value in values.items():
        contributions = live_contributions(entity.id, key) if value is not None and has_stat(entity, key) else []
        lifted[key] = clamp_to_field(entity, key, combine(value, contributions).value) if contributions and value is not None else value
    return set_stats(entity, **lifted)


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
