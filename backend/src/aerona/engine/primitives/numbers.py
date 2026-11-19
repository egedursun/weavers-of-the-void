import math
from collections.abc import Callable, Mapping, Sequence

from aerona.constants.engine import (
    FNV_OFFSET,
    FNV_PRIME,
    ORDINAL_DEFAULT_SUFFIX,
    ORDINAL_DIGIT_CYCLE,
    ORDINAL_SUFFIXES,
    ORDINAL_TEEN_CYCLE,
    ORDINAL_TEEN_FIRST,
    ORDINAL_TEEN_LAST,
    ROUND_HALF,
    U32_MASK,
    U32_SPAN,
)
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom


def round_half_up(value: float) -> int:
    return math.floor(value + ROUND_HALF)


def clamp_int(value: float, low: int, high: int) -> int:
    return max(low, min(high, round_half_up(value)))


def clamp_float(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def clamp_percent(value: float) -> int:
    return clamp_int(value, 0, PERCENT)


def fraction(percent: float) -> float:
    return percent / PERCENT


def saturating(value: float, half: float, cap: float) -> float:
    if value <= 0:
        return 0.0
    return cap * value / (value + max(1.0, half))


def decay_weight(keep_pct: float, age: int) -> float:
    return float((keep_pct / PERCENT) ** max(0, age))


def decayed_value(value: int, keep_pct: float, floor: int) -> int:
    kept = round_half_up(value * keep_pct / PERCENT)
    return 0 if abs(kept) < floor else kept


def roll_top[T](rng: SeededRandom, items: Sequence[T], count: int, key: Callable[[T], tuple[float | int, ...]] | None = None) -> T | None:
    pool = sorted(items, key=key) if key is not None else list(items)
    head = pool[: max(1, count)]
    return rng.pick(head) if head else None


def ordinal(number: int) -> str:
    teen = number % ORDINAL_TEEN_CYCLE
    if ORDINAL_TEEN_FIRST <= teen <= ORDINAL_TEEN_LAST:
        return f"{number}{ORDINAL_DEFAULT_SUFFIX}"
    suffix = ORDINAL_SUFFIXES.get(number % ORDINAL_DIGIT_CYCLE, ORDINAL_DEFAULT_SUFFIX)
    return f"{number}{suffix}"


def scaled_cap(base: int, divisor: int, communities: int) -> int:
    return base + (communities // divisor if divisor > 0 else 0)


def at_cap(count: int, cap: int) -> bool:
    return cap > 0 and count >= cap


def stochastic_round(value: float, roll: float) -> int:
    whole = math.floor(value)
    return whole + (1 if roll < value - whole else 0)


def stable_roll(key: int | str, salt: str) -> float:
    value = FNV_OFFSET
    for character in f"{key}:{salt}":
        value ^= ord(character)
        value = (value * FNV_PRIME) & U32_MASK
    return value / U32_SPAN


def apportion[Key](amount: int, weights: Mapping[Key, float]) -> dict[Key, int]:
    positive = [(key, float(weight)) for key, weight in weights.items() if weight > 0]
    mass = sum(weight for _, weight in positive)
    if amount <= 0 or mass <= 0:
        return {}
    quotas = [(key, amount * weight / mass) for key, weight in positive]
    found = {key: int(quota) for key, quota in quotas}
    left = amount - sum(found.values())
    for key, _ in sorted(quotas, key=lambda item: item[1] - int(item[1]), reverse=True)[:left]:
        found[key] += 1
    return found
