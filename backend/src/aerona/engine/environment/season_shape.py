from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from aerona.constants.calendar import SHARE_TOTAL
from aerona.core.random import SeededRandom
from aerona.domain.enums.environment import SeasonOnset, SeasonWarmth, SeasonWater

WARM_BAND = 0.8
COLD_BAND = 0.2
WATER_BANDS: tuple[tuple[int, SeasonWater], ...] = (
    (-50, SeasonWater.ARID),
    (-10, SeasonWater.DRY),
    (10, SeasonWater.EVEN),
    (50, SeasonWater.WET),
)
TRANSITIONS = frozenset({SeasonWarmth.WARMING, SeasonWarmth.COOLING})
TRANSITION_COUNT_MIN = 6
GOLDEN = 0.6180339887498949


class Shaped(Protocol):
    @property
    def position(self) -> int: ...

    @property
    def temperature_shift(self) -> int: ...

    @property
    def rain_shift(self) -> int: ...


class Shared(Shaped, Protocol):
    @property
    def share_pct(self) -> int: ...


@dataclass(frozen=True)
class SeasonPhase:
    warmth: SeasonWarmth
    water: SeasonWater


def warmth_of(seasons: Sequence[Shaped]) -> dict[int, SeasonWarmth]:
    ordered = sorted(seasons, key=lambda season: season.position)
    if not ordered:
        return {}
    low = min(season.temperature_shift for season in ordered)
    high = max(season.temperature_shift for season in ordered)
    if high == low:
        return {season.position: SeasonWarmth.EVEN for season in ordered}
    coldest = min(ordered, key=lambda season: (season.temperature_shift, season.position)).position
    warmest = max(ordered, key=lambda season: (season.temperature_shift, -season.position)).position
    found: dict[int, SeasonWarmth] = {}
    for index, season in enumerate(ordered):
        level = (season.temperature_shift - low) / (high - low)
        trend = ordered[(index + 1) % len(ordered)].temperature_shift - ordered[index - 1].temperature_shift
        if season.position == warmest:
            found[season.position] = SeasonWarmth.WARMEST
        elif season.position == coldest:
            found[season.position] = SeasonWarmth.COLDEST
        elif level >= WARM_BAND:
            found[season.position] = SeasonWarmth.WARM
        elif level <= COLD_BAND:
            found[season.position] = SeasonWarmth.COLD
        elif trend > 0:
            found[season.position] = SeasonWarmth.WARMING
        elif trend < 0:
            found[season.position] = SeasonWarmth.COOLING
        else:
            found[season.position] = SeasonWarmth.EVEN
    return found


def water_of(rain: int, mean: float) -> SeasonWater:
    offset = rain - mean
    return next((water for ceiling, water in WATER_BANDS if offset < ceiling), SeasonWater.DELUGE)


def season_phase(seasons: Sequence[Shaped]) -> dict[int, SeasonPhase]:
    warmth = warmth_of(seasons)
    mean = sum(season.rain_shift for season in seasons) / len(seasons) if seasons else 0.0
    return {season.position: SeasonPhase(warmth[season.position], water_of(season.rain_shift, mean)) for season in seasons}


def apportion(weights: Sequence[float], total: int = SHARE_TOTAL) -> list[int]:
    if not weights:
        return []
    whole = sum(weights)
    if whole <= 0:
        weights, whole = [1.0] * len(weights), float(len(weights))
    raw = [weight * total / whole for weight in weights]
    shares = [max(1, int(value)) for value in raw]
    order = sorted(range(len(raw)), key=lambda index: (-(raw[index] - int(raw[index])), index))
    step = 0
    while sum(shares) < total:
        shares[order[step % len(order)]] += 1
        step += 1
    while sum(shares) > total:
        largest = max(range(len(shares)), key=lambda index: (shares[index], -index))
        shares[largest] -= 1
    return shares


def drafted_shares(seasons: Sequence[Shaped], transition_share_pct: int) -> list[int]:
    ordered = sorted(seasons, key=lambda season: season.position)
    warmth = warmth_of(ordered)
    turning = [season for season in ordered if warmth[season.position] in TRANSITIONS] if len(ordered) >= TRANSITION_COUNT_MIN else []
    rest = len(ordered) - len(turning)
    if not turning or rest == 0 or transition_share_pct * len(turning) >= SHARE_TOTAL:
        return apportion([1.0] * len(ordered))
    left = SHARE_TOTAL - transition_share_pct * len(turning)
    weights = [float(transition_share_pct) if season in turning else left / rest for season in ordered]
    return apportion(weights)


def rebalanced(shares: Mapping[int, int], fixed: Mapping[int, int], held: frozenset[int] = frozenset()) -> dict[int, int]:
    keys = sorted(shares)
    pinned = {key: fixed[key] for key in keys if key in fixed}
    pinned |= {key: shares[key] for key in keys if key in held and key not in pinned}
    free = [key for key in keys if key not in pinned]
    if not free:
        return dict(zip(keys, apportion([float(pinned[key]) for key in keys]), strict=True))
    room = max(len(free), SHARE_TOTAL - sum(pinned.values()))
    spread = apportion([float(max(1, shares[key])) for key in free], room)
    result = {**pinned, **dict(zip(free, spread, strict=True))}
    if sum(result.values()) != SHARE_TOTAL:
        return dict(zip(keys, apportion([float(result[key]) for key in keys]), strict=True))
    return result


def season_at_fraction[S: Shared](seasons: Sequence[S], fraction: float) -> S | None:
    ordered = sorted(seasons, key=lambda season: season.position)
    if not ordered:
        return None
    return ordered[position_at_fraction([max(0, season.share_pct) for season in ordered], fraction)]


def position_at_fraction(shares: Sequence[int], fraction: float) -> int:
    total = sum(shares)
    if total <= 0:
        return min(len(shares) - 1, int(fraction * len(shares))) if shares else 0
    point = min(max(fraction, 0.0), 1.0 - 1e-9) * total
    reached = 0
    for position, share in enumerate(shares):
        reached += share
        if point < reached:
            return position
    return len(shares) - 1


def pick_season[S: Shared](seasons: Sequence[S], rng: SeededRandom) -> S | None:
    return season_at_fraction(seasons, rng.random())


def onset_draw(rng: SeededRandom, early_pct: int, late_pct: int, failed_pct: int) -> SeasonOnset:
    roll = rng.random() * SHARE_TOTAL
    if roll < failed_pct:
        return SeasonOnset.FAILED
    if roll < failed_pct + late_pct:
        return SeasonOnset.LATE
    if roll < failed_pct + late_pct + early_pct:
        return SeasonOnset.EARLY
    return SeasonOnset.ON_TIME


def index_fraction(index: int) -> float:
    return (index * GOLDEN) % 1.0


def season_of_index[S: Shared](seasons: Sequence[S], index: int) -> S | None:
    return season_at_fraction(seasons, index_fraction(index))


def season_of_warmth[S: Shared](seasons: Sequence[S], warmth: SeasonWarmth) -> S | None:
    phases = season_phase(seasons)
    return next((season for season in sorted(seasons, key=lambda item: item.position) if phases[season.position].warmth is warmth), None)


def wettest[S: Shared](seasons: Sequence[S]) -> S | None:
    return max(seasons, key=lambda season: (season.rain_shift, -season.position), default=None)
