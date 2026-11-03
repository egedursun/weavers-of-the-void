from collections.abc import Mapping

from aerona.catalog.mind import ACT_READINGS, MEMORIES
from aerona.constants.units import PERCENT
from aerona.db.tables.mind import VALUE_MAX, VALUE_MIN
from aerona.domain.enums.mind import ActKind, MemoryKind, ValueAxis
from aerona.engine.primitives.numbers import clamp_int

SPAN = VALUE_MAX - VALUE_MIN
DISTANCE_MAX = PERCENT
NEUTRAL_DISTANCE = DISTANCE_MAX // 2
Vector = Mapping[ValueAxis, int]


def value_distance(first: Vector, second: Vector) -> int:
    if not first or not second:
        return NEUTRAL_DISTANCE
    gaps = [abs(first.get(axis, 0) - second.get(axis, 0)) for axis in ValueAxis]
    return clamp_int(sum(gaps) / len(gaps) * DISTANCE_MAX / SPAN * 2, 0, DISTANCE_MAX)


def value_alignment(first: Vector, second: Vector) -> int:
    return NEUTRAL_DISTANCE - value_distance(first, second)


def value_reading(values: Vector, act: ActKind) -> int:
    weights = ACT_READINGS[act]
    return clamp_int(sum(values.get(axis, 0) * weight for axis, weight in weights.items()) / PERCENT, VALUE_MIN, VALUE_MAX)


def memory_weight(values: Vector, kind: MemoryKind, *, floor_pct: int, ceiling_pct: int) -> float:
    cares = MEMORIES[kind].cares
    lift = sum(values.get(axis, 0) * weight for axis, weight in cares.items()) / PERCENT
    return clamp_int(PERCENT + lift, floor_pct, ceiling_pct) / PERCENT


def blend(current: Vector, target: Vector, share_pct: float) -> dict[ValueAxis, int]:
    return {
        axis: clamp_int(current.get(axis, 0) + (target.get(axis, 0) - current.get(axis, 0)) * share_pct / PERCENT, VALUE_MIN, VALUE_MAX) for axis in ValueAxis
    }


def top_values(values: Vector, count: int) -> list[tuple[ValueAxis, int]]:
    return sorted(((axis, value) for axis, value in values.items() if value), key=lambda item: (-abs(item[1]), item[0]))[:count]
