import math
from dataclasses import dataclass, replace

from aerona.catalog.life_traits import WORLD_TYPE_TRAITS, having
from aerona.catalog.world_views import WORLD_VIEWS
from aerona.constants.calendar import SEASONS_MAX
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.domain.enums.life_traits import WorldTypeTrait
from aerona.domain.enums.world import WorldType
from aerona.engine.environment.season_shape import drafted_shares
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules

ORBIT_EXPONENT = 1.5
DRY, NEUTRAL, WET = -1, 0, 1
TWO = 2

ICE_SHAPE = (NEUTRAL, WET)
NO_SEASON_WORLDS = frozenset(world_type for world_type, view in WORLD_VIEWS.items() if not view.seasons)
TWO_SEASON_WORLDS = having(WORLD_TYPE_TRAITS, WorldTypeTrait.TWO_SEASON_WORLDS)


@dataclass(frozen=True)
class WorldCalendar:
    axial_tilt: int
    year_length_days: int
    season_count: int
    day_length_hours: int


@dataclass(frozen=True)
class SeasonDraft:
    position: int
    temperature_shift: int
    rain_shift: int
    growth: int
    travel: int
    campaign: int
    share_pct: int = 0


def warmest_of(count: int) -> int:
    return 0 if count <= TWO else 1


def wetness_pattern(count: int, wet_offset: int) -> tuple[int, ...]:
    if count <= 1:
        return (NEUTRAL,)
    peak = warmest_of(count)
    wet = (peak + wet_offset) % count
    return tuple(WET if position == wet else DRY if position == peak else NEUTRAL for position in range(count))


def season_count_for(rules: Rules, world_type: WorldType, axial_tilt: int) -> int:
    settings = rules.seasons
    if world_type in NO_SEASON_WORLDS:
        return 1
    if world_type in TWO_SEASON_WORLDS:
        return 2
    for count, ceiling in (
        (2, settings.two_seasons_below_tilt),
        (3, settings.three_seasons_below_tilt),
        (4, settings.four_seasons_below_tilt),
        (5, settings.five_seasons_below_tilt),
        (6, settings.six_seasons_below_tilt),
        (7, settings.seven_seasons_below_tilt),
    ):
        if axial_tilt < ceiling:
            return count
    return SEASONS_MAX


def world_calendar(rules: Rules, rng: SeededRandom, world_type: WorldType, orbit: float) -> WorldCalendar:
    settings = rules.seasons
    tilt = 0 if world_type in NO_SEASON_WORLDS else clamp_int(rng.integer(settings.tilt_min, settings.tilt_roll_max), 0, settings.tilt_max)
    if world_type in TWO_SEASON_WORLDS:
        tilt = clamp_int(tilt + settings.ice_tilt_bonus, 0, settings.tilt_max)
    year = clamp_int(settings.year_days_base * max(orbit, 0.0) ** ORBIT_EXPONENT, settings.year_days_min, settings.year_days_max)
    locked = world_type is WorldType.TIDALLY_LOCKED
    day = settings.locked_day_hours if locked else rng.integer(settings.day_hours_min, settings.day_hours_max)
    return WorldCalendar(axial_tilt=tilt, year_length_days=year, season_count=season_count_for(rules, world_type, tilt), day_length_hours=day)


def season_drafts(rules: Rules, world_type: WorldType, count: int, axial_tilt: int) -> list[SeasonDraft]:
    settings = rules.seasons
    count = max(1, min(SEASONS_MAX, count))
    pattern = ICE_SHAPE if world_type in TWO_SEASON_WORLDS and count == len(ICE_SHAPE) else wetness_pattern(count, settings.wet_offset)
    amplitude = axial_tilt / max(1, settings.tilt_max)
    peak = warmest_of(count)
    drafts: list[SeasonDraft] = []
    for position, wetness in enumerate(pattern):
        warmth = math.cos(math.tau * (position - peak) / count) if count > 1 else 0.0
        if world_type in TWO_SEASON_WORLDS:
            warmth = -1.0 if position == 0 else 1.0
        temperature = round_half_up(warmth * settings.temperature_swing * amplitude)
        rain = round_half_up(wetness * settings.rain_swing)
        drafts.append(
            SeasonDraft(
                position=position,
                temperature_shift=temperature,
                rain_shift=rain,
                growth=clamp_int(settings.growth_base + warmth * settings.growth_swing * amplitude + wetness * settings.growth_wet, 0, PERCENT),
                travel=clamp_int(
                    settings.travel_base - max(0.0, -warmth) * settings.travel_cold * amplitude - max(0, wetness) * settings.travel_wet, 0, PERCENT
                ),
                campaign=clamp_int(settings.campaign_base + warmth * settings.campaign_warm * amplitude - max(0, wetness) * settings.campaign_wet, 0, PERCENT),
            )
        )
    shares = drafted_shares(drafts, settings.transition_share_pct)
    return [replace(draft, share_pct=share) for draft, share in zip(drafts, shares, strict=True)]


def tidal_strength(rules: Rules, moons: int) -> int:
    return clamp_int(moons * rules.seasons.tide_per_moon, 0, PERCENT)
