from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.catalog.weather import WEATHER
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.core.total import total
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.environment import TerrainKind, WeatherDraw, WeatherEffect, WeatherKind
from aerona.domain.enums.world import SkyEventKind
from aerona.engine.primitives.numbers import clamp_int
from aerona.rules.registry import Rules

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


@dataclass(frozen=True)
class Climate:
    rules: Rules
    inputs: WeatherInputs
    cold: float
    hot: float
    dry: float
    wet: float


def aurora_draw(climate: Climate) -> float:
    settings = climate.rules.weather
    flare = settings.flare_aurora_pct / PERCENT if SkyEventKind.FLARE in climate.inputs.sky else 0.0
    return climate.cold * climate.inputs.latitude / PERCENT + flare


def magic_draw(climate: Climate) -> float:
    settings = climate.rules.weather
    return _ramp(climate.inputs.magic_density - settings.magic_storm_threshold, PERCENT - settings.magic_storm_threshold)


def ash_draw(climate: Climate) -> float:
    settings = climate.rules.weather
    volcanic = settings.volcanic_ash_pct if climate.inputs.terrain is TerrainKind.VOLCANIC else 0
    supernova = settings.supernova_ash_pct if SkyEventKind.SUPERNOVA in climate.inputs.sky else 0
    return (volcanic + supernova) / PERCENT


def void_draw(climate: Climate) -> float:
    settings = climate.rules.weather
    storm = settings.void_storm_rain_pct / PERCENT if SkyEventKind.VOID_STORM in climate.inputs.sky else 0.0
    return _ramp(climate.inputs.leakage - settings.void_rain_threshold, PERCENT - settings.void_rain_threshold) + storm


DRAWS: Mapping[WeatherDraw, Callable[[Climate], float]] = total(
    WeatherDraw,
    {
        WeatherDraw.COLD: lambda climate: climate.cold,
        WeatherDraw.HOT: lambda climate: climate.hot,
        WeatherDraw.DRY: lambda climate: climate.dry,
        WeatherDraw.DRY_HOT: lambda climate: climate.dry * climate.hot,
        WeatherDraw.WET: lambda climate: climate.wet,
        WeatherDraw.WET_LIQUID: lambda climate: climate.wet * (1 - climate.cold),
        WeatherDraw.CLEAR: lambda climate: 1 + climate.dry,
        WeatherDraw.EVEN: lambda climate: 1.0,
        WeatherDraw.AURORA: aurora_draw,
        WeatherDraw.MAGIC: magic_draw,
        WeatherDraw.ASH: ash_draw,
        WeatherDraw.VOID: void_draw,
        WeatherDraw.ECLIPSE: lambda climate: 1.0 if climate.inputs.sky & SKY_DARKNESS else 0.0,
    },
)


def weather_weights(rules: Rules, inputs: WeatherInputs) -> dict[WeatherKind, float]:
    settings = rules.weather
    temperature = inputs.temperature + inputs.season_temperature
    rain = clamp_int(inputs.rainfall + inputs.season_rain, 0, PERCENT)
    climate = Climate(
        rules,
        inputs,
        cold=_ramp(settings.cold_threshold - temperature, settings.cold_span),
        hot=_ramp(temperature - settings.hot_threshold, settings.hot_span),
        dry=_ramp(settings.dry_threshold - rain, settings.dry_span),
        wet=rain / settings.wet_pivot,
    )
    return {kind: max(0.0, float(spec.weight(rules)) * DRAWS[spec.draw](climate)) for kind, spec in WEATHER.items()}


def weather_of(rules: Rules, kind: WeatherKind) -> Weather:
    spec = WEATHER[kind]
    return Weather(kind, spec.label, spec.effects(rules))


def draw_weather(rules: Rules, rng: SeededRandom, inputs: WeatherInputs) -> Weather:
    weights = weather_weights(rules, inputs)
    kinds = [kind for kind in WeatherKind if weights[kind] > 0]
    kind = rng.weighted(kinds, [weights[item] for item in kinds]) if kinds else WeatherKind.CLEAR
    return weather_of(rules, kind)


def weather_stream(region_id: int, slot: str) -> str:
    return f"weather.{region_id}.{slot}"


def weather_at(rules: Rules, world_seed: int, epoch: int, slot: str, inputs: WeatherInputs) -> Weather:
    return draw_weather(rules, SeededRandom.for_epoch(world_seed, epoch, weather_stream(inputs.region_id, slot)), inputs)
