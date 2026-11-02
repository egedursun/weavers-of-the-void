from dataclasses import dataclass

from aerona.catalog.weather import WEATHER
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.environment import TerrainKind, WeatherEffect, WeatherKind
from aerona.domain.enums.world import SkyEventKind
from aerona.engine.primitives.numbers import clamp_int
from aerona.rules.registry import Rules

COLD_KINDS = frozenset({WeatherKind.SNOW, WeatherKind.BLIZZARD})
HOT_KINDS = frozenset({WeatherKind.HEAT_WAVE})
DRY_KINDS = frozenset({WeatherKind.DROUGHT_WIND, WeatherKind.SANDSTORM})
WET_KINDS = frozenset({WeatherKind.RAIN, WeatherKind.DOWNPOUR, WeatherKind.STORM, WeatherKind.FOG, WeatherKind.HAIL})
LIQUID_KINDS = frozenset({WeatherKind.RAIN, WeatherKind.DOWNPOUR})
SKY_DARKNESS = frozenset({SkyEventKind.ECLIPSE, SkyEventKind.BLACK_SUN})


@dataclass(frozen=True)
class WeatherInputs:
    region_id: int
    temperature: int
    rainfall: int
    latitude: int
    magic_density: int
    terrain: TerrainKind
    leakage: int = 0
    season_temperature: int = 0
    season_rain: int = 0
    sky: frozenset[SkyEventKind] = frozenset()


@dataclass(frozen=True)
class Weather:
    kind: WeatherKind
    label: str
    effects: dict[WeatherEffect, int]

    def effect(self, effect: WeatherEffect) -> int:
        return self.effects[effect]

    def factor(self, effect: WeatherEffect) -> float:
        return 1 + self.effects[effect] / PERCENT

    def omen_for(self, domains: frozenset[Domain]) -> int:
        omen = self.effects[WeatherEffect.MORALE]
        return abs(omen) if domains & WEATHER[self.kind].favoured_by else omen


def _ramp(value: float, span: int) -> float:
    return min(1.0, max(0.0, value / max(1, span)))


def weather_weights(rules: Rules, inputs: WeatherInputs) -> dict[WeatherKind, float]:
    settings = rules.weather
    temperature = inputs.temperature + inputs.season_temperature
    rain = clamp_int(inputs.rainfall + inputs.season_rain, 0, PERCENT)
    cold = _ramp(settings.cold_threshold - temperature, settings.cold_span)
    hot = _ramp(temperature - settings.hot_threshold, settings.hot_span)
    dry = _ramp(settings.dry_threshold - rain, settings.dry_span)
    wet = rain / settings.wet_pivot
    weights: dict[WeatherKind, float] = {}
    for kind, spec in WEATHER.items():
        weight = float(spec.weight(rules))
        if kind in COLD_KINDS:
            weight *= cold
        elif kind in HOT_KINDS:
            weight *= hot
        elif kind in DRY_KINDS:
            weight *= dry * (hot if kind is WeatherKind.SANDSTORM else 1.0)
        elif kind in WET_KINDS:
            weight *= wet * ((1 - cold) if kind in LIQUID_KINDS else 1.0)
        elif kind is WeatherKind.CLEAR:
            weight *= 1 + dry
        elif kind is WeatherKind.AURORA:
            weight *= cold * inputs.latitude / PERCENT
        elif kind is WeatherKind.MAGIC_STORM:
            weight *= _ramp(inputs.magic_density - settings.magic_storm_threshold, PERCENT - settings.magic_storm_threshold)
        elif kind is WeatherKind.ASH_FALL:
            volcanic = settings.volcanic_ash_pct if inputs.terrain is TerrainKind.VOLCANIC else 0
            supernova = settings.supernova_ash_pct if SkyEventKind.SUPERNOVA in inputs.sky else 0
            weight *= (volcanic + supernova) / PERCENT
        elif kind is WeatherKind.VOID_RAIN:
            storm = settings.void_storm_rain_pct / PERCENT if SkyEventKind.VOID_STORM in inputs.sky else 0.0
            weight *= _ramp(inputs.leakage - settings.void_rain_threshold, PERCENT - settings.void_rain_threshold) + storm
        elif kind is WeatherKind.ECLIPSE_DARK:
            weight *= 1.0 if inputs.sky & SKY_DARKNESS else 0.0
        weights[kind] = max(0.0, weight)
    return weights


def draw_weather(rules: Rules, rng: SeededRandom, inputs: WeatherInputs) -> Weather:
    weights = weather_weights(rules, inputs)
    kinds = [kind for kind in WeatherKind if weights[kind] > 0]
    kind = rng.weighted(kinds, [weights[item] for item in kinds]) if kinds else WeatherKind.CLEAR
    spec = WEATHER[kind]
    return Weather(kind, spec.label, spec.effects(rules))


def weather_stream(region_id: int, slot: str) -> str:
    return f"weather.{region_id}.{slot}"


def weather_at(rules: Rules, world_seed: int, epoch: int, slot: str, inputs: WeatherInputs) -> Weather:
    return draw_weather(rules, SeededRandom.for_epoch(world_seed, epoch, weather_stream(inputs.region_id, slot)), inputs)
