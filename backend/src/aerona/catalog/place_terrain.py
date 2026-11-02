from collections.abc import Callable
from dataclasses import dataclass

from aerona.domain.enums.environment import PlaceCover, TerrainKind, WaterSource
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class PlaceProfile:
    terrain: TerrainKind | None
    cover: PlaceCover
    water: WaterSource
    height: Callable[[Rules], int]
    chokepoint: bool = False


def _none(rules: Rules) -> int:
    return 0


def _low(rules: Rules) -> int:
    return rules.environment.place_height_low


def _high(rules: Rules) -> int:
    return rules.environment.place_height_high


DEFAULT_PROFILE = PlaceProfile(None, PlaceCover.LIGHT, WaterSource.NONE, _none)

PLACE_PROFILES: dict[str, PlaceProfile] = {
    "forest": PlaceProfile(TerrainKind.FOREST, PlaceCover.HEAVY, WaterSource.SPRING, _none),
    "misty grove": PlaceProfile(TerrainKind.FOREST, PlaceCover.HEAVY, WaterSource.SPRING, _none),
    "lake": PlaceProfile(None, PlaceCover.OPEN, WaterSource.LAKE, _none),
    "valley": PlaceProfile(TerrainKind.RIVER_VALLEY, PlaceCover.LIGHT, WaterSource.RIVER, _none),
    "river": PlaceProfile(TerrainKind.RIVER_VALLEY, PlaceCover.OPEN, WaterSource.RIVER, _none, chokepoint=True),
    "cave": PlaceProfile(TerrainKind.UNDERGROUND, PlaceCover.HEAVY, WaterSource.SPRING, _low, chokepoint=True),
    "marsh": PlaceProfile(TerrainKind.MARSH, PlaceCover.LIGHT, WaterSource.LAKE, _none),
    "pass": PlaceProfile(TerrainKind.HIGH_PASS, PlaceCover.LIGHT, WaterSource.NONE, _high, chokepoint=True),
    "chasm": PlaceProfile(TerrainKind.CANYON, PlaceCover.LIGHT, WaterSource.NONE, _high, chokepoint=True),
    "well": PlaceProfile(None, PlaceCover.OPEN, WaterSource.WELL, _none),
    "stone circle": PlaceProfile(None, PlaceCover.OPEN, WaterSource.NONE, _low),
    "hill": PlaceProfile(TerrainKind.HILLS, PlaceCover.LIGHT, WaterSource.NONE, _high),
    "upland": PlaceProfile(TerrainKind.HILLS, PlaceCover.LIGHT, WaterSource.SPRING, _high),
    "plain": PlaceProfile(TerrainKind.PLAIN, PlaceCover.OPEN, WaterSource.NONE, _none),
    "cove": PlaceProfile(TerrainKind.COAST, PlaceCover.LIGHT, WaterSource.SEA, _low),
    "island": PlaceProfile(TerrainKind.ISLAND, PlaceCover.LIGHT, WaterSource.SEA, _low),
    "reef": PlaceProfile(TerrainKind.COAST, PlaceCover.OPEN, WaterSource.SEA, _none, chokepoint=True),
    "oasis": PlaceProfile(TerrainKind.DESERT, PlaceCover.LIGHT, WaterSource.SPRING, _none),
    "dune": PlaceProfile(TerrainKind.DESERT, PlaceCover.LIGHT, WaterSource.NONE, _low),
    "glacier": PlaceProfile(TerrainKind.ICE_SHEET, PlaceCover.OPEN, WaterSource.NONE, _low),
    "hot spring": PlaceProfile(None, PlaceCover.OPEN, WaterSource.SPRING, _none),
    "lava lake": PlaceProfile(TerrainKind.VOLCANIC, PlaceCover.OPEN, WaterSource.NONE, _none),
    "ash plain": PlaceProfile(TerrainKind.VOLCANIC, PlaceCover.OPEN, WaterSource.NONE, _none),
}

TERRAIN_NATURES: dict[TerrainKind, tuple[str, ...]] = {
    TerrainKind.MOUNTAINS: ("pass", "cave", "chasm"),
    TerrainKind.HILLS: ("hill", "upland", "cave"),
    TerrainKind.CANYON: ("chasm", "pass"),
    TerrainKind.MARSH: ("marsh", "lake"),
    TerrainKind.FOREST: ("forest", "misty grove"),
    TerrainKind.JUNGLE: ("forest", "marsh"),
    TerrainKind.RIVER_VALLEY: ("river", "valley"),
    TerrainKind.COAST: ("cove",),
    TerrainKind.DESERT: ("dune", "oasis"),
    TerrainKind.STEPPE: ("plain",),
    TerrainKind.PLAIN: ("plain", "river"),
}


def place_profile(subtype: str | None) -> PlaceProfile:
    return PLACE_PROFILES.get((subtype or "").strip().lower(), DEFAULT_PROFILE)
