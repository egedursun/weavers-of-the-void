import math
from dataclasses import dataclass

from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.domain.enums.world import WorldType
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules

ORBIT_EXPONENT = 1.5
DRY, NEUTRAL, WET = -1, 0, 1

SEASON_SHAPES: dict[int, tuple[tuple[str, int], ...]] = {
    1: (("Endless Day", NEUTRAL),),
    2: (("Wet Season", WET), ("Dry Season", DRY)),
    3: (("Inundation", WET), ("Growing", NEUTRAL), ("Harvest", DRY)),
    4: (("Spring", NEUTRAL), ("Summer", DRY), ("Autumn", NEUTRAL), ("Winter", NEUTRAL)),
    5: (("Spring", NEUTRAL), ("Summer", DRY), ("Monsoon", WET), ("Autumn", NEUTRAL), ("Winter", NEUTRAL)),
    6: (("Spring", NEUTRAL), ("Summer", DRY), ("Monsoon", WET), ("Autumn", NEUTRAL), ("Early Winter", NEUTRAL), ("Deep Winter", NEUTRAL)),
}
ICE_SHAPE = (("Long Winter", NEUTRAL), ("Short Thaw", WET))
WARMEST: dict[int, int] = {1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 1}
NO_SEASON_WORLDS = frozenset({WorldType.TIDALLY_LOCKED, WorldType.GENERATION_SHIP, WorldType.VOID_POCKET, WorldType.GODS_PALACE})
TWO_SEASON_WORLDS = frozenset({WorldType.ICE})


@dataclass(frozen=True)
class WorldCalendar:
    axial_tilt: int
    year_length_days: int
    season_count: int
    day_length_hours: int


@dataclass(frozen=True)
class SeasonDraft:
    position: int
    name: str
    temperature_shift: int
    rain_shift: int
    growth: int
    travel: int
    campaign: int


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
    ):
        if axial_tilt < ceiling:
            return count
    return max(SEASON_SHAPES)


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
    shapes = ICE_SHAPE if world_type in TWO_SEASON_WORLDS and count == len(ICE_SHAPE) else SEASON_SHAPES[count]
    amplitude = axial_tilt / max(1, settings.tilt_max)
    peak = WARMEST[count]
    drafts: list[SeasonDraft] = []
    for position, (name, wetness) in enumerate(shapes):
        warmth = math.cos(math.tau * (position - peak) / count) if count > 1 else 0.0
        if world_type in TWO_SEASON_WORLDS:
            warmth = -1.0 if position == 0 else 1.0
        temperature = round_half_up(warmth * settings.temperature_swing * amplitude)
        rain = round_half_up(wetness * settings.rain_swing)
        drafts.append(
            SeasonDraft(
                position=position,
                name=name,
                temperature_shift=temperature,
                rain_shift=rain,
                growth=clamp_int(settings.growth_base + warmth * settings.growth_swing * amplitude + wetness * settings.growth_wet, 0, PERCENT),
                travel=clamp_int(
                    settings.travel_base - max(0.0, -warmth) * settings.travel_cold * amplitude - max(0, wetness) * settings.travel_wet, 0, PERCENT
                ),
                campaign=clamp_int(settings.campaign_base + warmth * settings.campaign_warm * amplitude - max(0, wetness) * settings.campaign_wet, 0, PERCENT),
            )
        )
    return drafts


def tidal_strength(rules: Rules, moons: int) -> int:
    return clamp_int(moons * rules.seasons.tide_per_moon, 0, PERCENT)
