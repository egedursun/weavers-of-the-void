import re
from pathlib import Path

from aerona.catalog.weather import WEATHER, has_trait, with_trait
from aerona.domain.enums.environment import WeatherDraw, WeatherKind, WeatherTrait
from aerona.engine.environment.weather import DRAWS
from aerona.rules.registry import Rules

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"


def readers_of(trait: WeatherTrait) -> list[str]:
    pattern = re.compile(rf"\bWeatherTrait\.{trait.name}\b")
    return [str(path) for path in SOURCE.rglob("*.py") if "catalog" not in path.parts and pattern.search(path.read_text(encoding="utf-8"))]


def test_every_weather_kind_has_a_draw_traits_and_unit_factors_that_are_rules() -> None:
    rules = Rules()
    assert set(WEATHER) == set(WeatherKind)
    for kind, spec in WEATHER.items():
        assert isinstance(spec.draw, WeatherDraw) and all(isinstance(trait, WeatherTrait) for trait in spec.traits)
        assert all(isinstance(value, int) for value in spec.unit_factors(rules).values()), kind
    assert set(DRAWS) == set(WeatherDraw)


def test_every_trait_is_read_outside_the_catalogue() -> None:
    assert [trait for trait in WeatherTrait if not readers_of(trait)] == []


def test_traits_keep_the_sets_they_replace() -> None:
    assert with_trait(WeatherTrait.COLD) == {
        WeatherKind.SNOW,
        WeatherKind.BLIZZARD,
        WeatherKind.SLEET,
        WeatherKind.FROST,
        WeatherKind.ICE_STORM,
        WeatherKind.FREEZING_FOG,
    }
    assert with_trait(WeatherTrait.LIQUID) == {
        WeatherKind.RAIN,
        WeatherKind.DOWNPOUR,
        WeatherKind.DRIZZLE,
        WeatherKind.THUNDERSTORM,
        WeatherKind.CYCLONE,
        WeatherKind.ICE_STORM,
    }
    assert has_trait(WeatherKind.SANDSTORM, WeatherTrait.COVERING) and not has_trait(None, WeatherTrait.COVERING)
