from collections.abc import Callable
from dataclasses import dataclass

from aerona.domain.enums.domain import Domain
from aerona.domain.enums.environment import WeatherEffect, WeatherKind
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class WeatherSpec:
    kind: WeatherKind
    label: str
    weight: Callable[[Rules], int]
    effects: Callable[[Rules], dict[WeatherEffect, int]]
    favoured_by: frozenset[Domain]


WEATHER: dict[WeatherKind, WeatherSpec] = {
    spec.kind: spec
    for spec in (
        WeatherSpec(
            WeatherKind.CLEAR,
            "Clear sky",
            lambda rules: rules.weather.clear_weight,
            lambda rules: {
                WeatherEffect.VISIBILITY: rules.weather.clear_visibility,
                WeatherEffect.FOOTING: rules.weather.clear_footing,
                WeatherEffect.COLD: rules.weather.clear_cold,
                WeatherEffect.HEAT: rules.weather.clear_heat,
                WeatherEffect.WET: rules.weather.clear_wet,
                WeatherEffect.WIND: rules.weather.clear_wind,
                WeatherEffect.MORALE: rules.weather.clear_morale,
                WeatherEffect.GROWTH: rules.weather.clear_growth,
            },
            frozenset({Domain.SUN, Domain.LIGHT}),
        ),
        WeatherSpec(
            WeatherKind.OVERCAST,
            "Overcast",
            lambda rules: rules.weather.overcast_weight,
            lambda rules: {
                WeatherEffect.VISIBILITY: rules.weather.overcast_visibility,
                WeatherEffect.FOOTING: rules.weather.overcast_footing,
                WeatherEffect.COLD: rules.weather.overcast_cold,
                WeatherEffect.HEAT: rules.weather.overcast_heat,
                WeatherEffect.WET: rules.weather.overcast_wet,
                WeatherEffect.WIND: rules.weather.overcast_wind,
                WeatherEffect.MORALE: rules.weather.overcast_morale,
                WeatherEffect.GROWTH: rules.weather.overcast_growth,
            },
            frozenset({Domain.SHADOW}),
        ),
        WeatherSpec(
            WeatherKind.RAIN,
            "Rain",
            lambda rules: rules.weather.rain_weight,
            lambda rules: {
                WeatherEffect.VISIBILITY: rules.weather.rain_visibility,
                WeatherEffect.FOOTING: rules.weather.rain_footing,
                WeatherEffect.COLD: rules.weather.rain_cold,
                WeatherEffect.HEAT: rules.weather.rain_heat,
                WeatherEffect.WET: rules.weather.rain_wet,
                WeatherEffect.WIND: rules.weather.rain_wind,
                WeatherEffect.MORALE: rules.weather.rain_morale,
                WeatherEffect.GROWTH: rules.weather.rain_growth,
            },
            frozenset({Domain.HARVEST, Domain.PLANTS, Domain.SEA}),
        ),
        WeatherSpec(
            WeatherKind.DOWNPOUR,
            "Downpour",
            lambda rules: rules.weather.downpour_weight,
            lambda rules: {
                WeatherEffect.VISIBILITY: rules.weather.downpour_visibility,
                WeatherEffect.FOOTING: rules.weather.downpour_footing,
                WeatherEffect.COLD: rules.weather.downpour_cold,
                WeatherEffect.HEAT: rules.weather.downpour_heat,
                WeatherEffect.WET: rules.weather.downpour_wet,
                WeatherEffect.WIND: rules.weather.downpour_wind,
                WeatherEffect.MORALE: rules.weather.downpour_morale,
                WeatherEffect.GROWTH: rules.weather.downpour_growth,
            },
            frozenset({Domain.SEA, Domain.STORM}),
        ),
        WeatherSpec(
            WeatherKind.STORM,
            "Storm",
            lambda rules: rules.weather.storm_weight,
            lambda rules: {
                WeatherEffect.VISIBILITY: rules.weather.storm_visibility,
                WeatherEffect.FOOTING: rules.weather.storm_footing,
                WeatherEffect.COLD: rules.weather.storm_cold,
                WeatherEffect.HEAT: rules.weather.storm_heat,
                WeatherEffect.WET: rules.weather.storm_wet,
                WeatherEffect.WIND: rules.weather.storm_wind,
                WeatherEffect.MORALE: rules.weather.storm_morale,
                WeatherEffect.GROWTH: rules.weather.storm_growth,
            },
            frozenset({Domain.STORM, Domain.SKY}),
        ),
        WeatherSpec(
            WeatherKind.FOG,
            "Fog",
            lambda rules: rules.weather.fog_weight,
            lambda rules: {
                WeatherEffect.VISIBILITY: rules.weather.fog_visibility,
                WeatherEffect.FOOTING: rules.weather.fog_footing,
                WeatherEffect.COLD: rules.weather.fog_cold,
                WeatherEffect.HEAT: rules.weather.fog_heat,
                WeatherEffect.WET: rules.weather.fog_wet,
                WeatherEffect.WIND: rules.weather.fog_wind,
                WeatherEffect.MORALE: rules.weather.fog_morale,
                WeatherEffect.GROWTH: rules.weather.fog_growth,
            },
            frozenset({Domain.SHADOW, Domain.DREAM, Domain.TRICKERY}),
        ),
        WeatherSpec(
            WeatherKind.SNOW,
            "Snow",
            lambda rules: rules.weather.snow_weight,
            lambda rules: {
                WeatherEffect.VISIBILITY: rules.weather.snow_visibility,
                WeatherEffect.FOOTING: rules.weather.snow_footing,
                WeatherEffect.COLD: rules.weather.snow_cold,
                WeatherEffect.HEAT: rules.weather.snow_heat,
                WeatherEffect.WET: rules.weather.snow_wet,
                WeatherEffect.WIND: rules.weather.snow_wind,
                WeatherEffect.MORALE: rules.weather.snow_morale,
                WeatherEffect.GROWTH: rules.weather.snow_growth,
            },
            frozenset({Domain.ICE}),
        ),
        WeatherSpec(
            WeatherKind.BLIZZARD,
            "Blizzard",
            lambda rules: rules.weather.blizzard_weight,
            lambda rules: {
                WeatherEffect.VISIBILITY: rules.weather.blizzard_visibility,
                WeatherEffect.FOOTING: rules.weather.blizzard_footing,
                WeatherEffect.COLD: rules.weather.blizzard_cold,
                WeatherEffect.HEAT: rules.weather.blizzard_heat,
                WeatherEffect.WET: rules.weather.blizzard_wet,
                WeatherEffect.WIND: rules.weather.blizzard_wind,
                WeatherEffect.MORALE: rules.weather.blizzard_morale,
                WeatherEffect.GROWTH: rules.weather.blizzard_growth,
            },
            frozenset({Domain.ICE, Domain.STORM}),
        ),
        WeatherSpec(
            WeatherKind.HEAT_WAVE,
            "Heat wave",
            lambda rules: rules.weather.heat_wave_weight,
            lambda rules: {
                WeatherEffect.VISIBILITY: rules.weather.heat_wave_visibility,
                WeatherEffect.FOOTING: rules.weather.heat_wave_footing,
                WeatherEffect.COLD: rules.weather.heat_wave_cold,
                WeatherEffect.HEAT: rules.weather.heat_wave_heat,
                WeatherEffect.WET: rules.weather.heat_wave_wet,
                WeatherEffect.WIND: rules.weather.heat_wave_wind,
                WeatherEffect.MORALE: rules.weather.heat_wave_morale,
                WeatherEffect.GROWTH: rules.weather.heat_wave_growth,
            },
            frozenset({Domain.SUN, Domain.FIRE}),
        ),
        WeatherSpec(
            WeatherKind.DROUGHT_WIND,
            "Drought wind",
            lambda rules: rules.weather.drought_wind_weight,
            lambda rules: {
                WeatherEffect.VISIBILITY: rules.weather.drought_wind_visibility,
                WeatherEffect.FOOTING: rules.weather.drought_wind_footing,
                WeatherEffect.COLD: rules.weather.drought_wind_cold,
                WeatherEffect.HEAT: rules.weather.drought_wind_heat,
                WeatherEffect.WET: rules.weather.drought_wind_wet,
                WeatherEffect.WIND: rules.weather.drought_wind_wind,
                WeatherEffect.MORALE: rules.weather.drought_wind_morale,
                WeatherEffect.GROWTH: rules.weather.drought_wind_growth,
            },
            frozenset({Domain.SUN, Domain.HUNGER}),
        ),
        WeatherSpec(
            WeatherKind.SANDSTORM,
            "Sandstorm",
            lambda rules: rules.weather.sandstorm_weight,
            lambda rules: {
                WeatherEffect.VISIBILITY: rules.weather.sandstorm_visibility,
                WeatherEffect.FOOTING: rules.weather.sandstorm_footing,
                WeatherEffect.COLD: rules.weather.sandstorm_cold,
                WeatherEffect.HEAT: rules.weather.sandstorm_heat,
                WeatherEffect.WET: rules.weather.sandstorm_wet,
                WeatherEffect.WIND: rules.weather.sandstorm_wind,
                WeatherEffect.MORALE: rules.weather.sandstorm_morale,
                WeatherEffect.GROWTH: rules.weather.sandstorm_growth,
            },
            frozenset({Domain.SKY, Domain.SALT}),
        ),
        WeatherSpec(
            WeatherKind.HAIL,
            "Hail",
            lambda rules: rules.weather.hail_weight,
            lambda rules: {
                WeatherEffect.VISIBILITY: rules.weather.hail_visibility,
                WeatherEffect.FOOTING: rules.weather.hail_footing,
                WeatherEffect.COLD: rules.weather.hail_cold,
                WeatherEffect.HEAT: rules.weather.hail_heat,
                WeatherEffect.WET: rules.weather.hail_wet,
                WeatherEffect.WIND: rules.weather.hail_wind,
                WeatherEffect.MORALE: rules.weather.hail_morale,
                WeatherEffect.GROWTH: rules.weather.hail_growth,
            },
            frozenset({Domain.STORM, Domain.STONE}),
        ),
        WeatherSpec(
            WeatherKind.MAGIC_STORM,
            "Magic storm",
            lambda rules: rules.weather.magic_storm_weight,
            lambda rules: {
                WeatherEffect.VISIBILITY: rules.weather.magic_storm_visibility,
                WeatherEffect.FOOTING: rules.weather.magic_storm_footing,
                WeatherEffect.COLD: rules.weather.magic_storm_cold,
                WeatherEffect.HEAT: rules.weather.magic_storm_heat,
                WeatherEffect.WET: rules.weather.magic_storm_wet,
                WeatherEffect.WIND: rules.weather.magic_storm_wind,
                WeatherEffect.MORALE: rules.weather.magic_storm_morale,
                WeatherEffect.GROWTH: rules.weather.magic_storm_growth,
            },
            frozenset({Domain.KNOWLEDGE, Domain.MADNESS}),
        ),
        WeatherSpec(
            WeatherKind.ASH_FALL,
            "Ash fall",
            lambda rules: rules.weather.ash_fall_weight,
            lambda rules: {
                WeatherEffect.VISIBILITY: rules.weather.ash_fall_visibility,
                WeatherEffect.FOOTING: rules.weather.ash_fall_footing,
                WeatherEffect.COLD: rules.weather.ash_fall_cold,
                WeatherEffect.HEAT: rules.weather.ash_fall_heat,
                WeatherEffect.WET: rules.weather.ash_fall_wet,
                WeatherEffect.WIND: rules.weather.ash_fall_wind,
                WeatherEffect.MORALE: rules.weather.ash_fall_morale,
                WeatherEffect.GROWTH: rules.weather.ash_fall_growth,
            },
            frozenset({Domain.ASH, Domain.FIRE}),
        ),
        WeatherSpec(
            WeatherKind.VOID_RAIN,
            "Void rain",
            lambda rules: rules.weather.void_rain_weight,
            lambda rules: {
                WeatherEffect.VISIBILITY: rules.weather.void_rain_visibility,
                WeatherEffect.FOOTING: rules.weather.void_rain_footing,
                WeatherEffect.COLD: rules.weather.void_rain_cold,
                WeatherEffect.HEAT: rules.weather.void_rain_heat,
                WeatherEffect.WET: rules.weather.void_rain_wet,
                WeatherEffect.WIND: rules.weather.void_rain_wind,
                WeatherEffect.MORALE: rules.weather.void_rain_morale,
                WeatherEffect.GROWTH: rules.weather.void_rain_growth,
            },
            frozenset({Domain.MADNESS}),
        ),
        WeatherSpec(
            WeatherKind.ECLIPSE_DARK,
            "Eclipse darkness",
            lambda rules: rules.weather.eclipse_dark_weight,
            lambda rules: {
                WeatherEffect.VISIBILITY: rules.weather.eclipse_dark_visibility,
                WeatherEffect.FOOTING: rules.weather.eclipse_dark_footing,
                WeatherEffect.COLD: rules.weather.eclipse_dark_cold,
                WeatherEffect.HEAT: rules.weather.eclipse_dark_heat,
                WeatherEffect.WET: rules.weather.eclipse_dark_wet,
                WeatherEffect.WIND: rules.weather.eclipse_dark_wind,
                WeatherEffect.MORALE: rules.weather.eclipse_dark_morale,
                WeatherEffect.GROWTH: rules.weather.eclipse_dark_growth,
            },
            frozenset({Domain.MOON, Domain.SHADOW}),
        ),
        WeatherSpec(
            WeatherKind.AURORA,
            "Aurora",
            lambda rules: rules.weather.aurora_weight,
            lambda rules: {
                WeatherEffect.VISIBILITY: rules.weather.aurora_visibility,
                WeatherEffect.FOOTING: rules.weather.aurora_footing,
                WeatherEffect.COLD: rules.weather.aurora_cold,
                WeatherEffect.HEAT: rules.weather.aurora_heat,
                WeatherEffect.WET: rules.weather.aurora_wet,
                WeatherEffect.WIND: rules.weather.aurora_wind,
                WeatherEffect.MORALE: rules.weather.aurora_morale,
                WeatherEffect.GROWTH: rules.weather.aurora_growth,
            },
            frozenset({Domain.STAR, Domain.LIGHT, Domain.SKY}),
        ),
    )
}

SEASON_DOMAINS = frozenset({Domain.SKY, Domain.STORM, Domain.TIME, Domain.SUN, Domain.MOON, Domain.HARVEST, Domain.ICE, Domain.PLANTS})
SEASON_DOMAIN_WORDS = ", ".join(domain.value for domain in Domain if domain in SEASON_DOMAINS)
