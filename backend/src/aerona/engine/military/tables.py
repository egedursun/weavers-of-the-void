from aerona.catalog.units import DEFENDER_TERRAIN, TACTIC_COUNTERS, TERRAIN_EFFECTS, WEATHER_EFFECTS
from aerona.constants.units import PERCENT
from aerona.domain.enums.environment import TerrainKind, WeatherKind
from aerona.domain.enums.military import Tactic, UnitFamily, UnitKind
from aerona.rules.registry import Rules


def terrain_cell(rules: Rules, terrain: TerrainKind | None, family: UnitFamily) -> float:
    if terrain is None or family not in TERRAIN_EFFECTS.get(terrain, {}):
        return 1.0
    return int(getattr(rules.battle_terrain, f"{terrain.value}_{family.value}_pct")) / PERCENT


def unit_terrain(rules: Rules, kind: UnitKind, terrain: TerrainKind | None, affinities: dict[TerrainKind, float]) -> float:
    if terrain is None or terrain not in affinities:
        return 1.0
    key = f"{kind.value}_{terrain.value}_pct"
    return int(getattr(rules.battle_terrain, key)) / PERCENT if hasattr(rules.battle_terrain, key) else affinities[terrain]


def defender_cell(rules: Rules, terrain: TerrainKind | None) -> float:
    if terrain is None or terrain not in DEFENDER_TERRAIN:
        return 1.0
    return int(getattr(rules.battle_terrain, f"{terrain.value}_defender_pct")) / PERCENT


def weather_cell(rules: Rules, weather: WeatherKind | None, family: UnitFamily) -> float:
    if weather is None or family not in WEATHER_EFFECTS.get(weather, {}):
        return 1.0
    return int(getattr(rules.battle_weather, f"{weather.value}_{family.value}_pct")) / PERCENT


def counters(mine: Tactic, theirs: Tactic) -> bool:
    return theirs in TACTIC_COUNTERS.get(mine, frozenset())


def matchup(rules: Rules, mine: Tactic, theirs: Tactic) -> float:
    if not counters(mine, theirs):
        return 1.0
    return int(getattr(rules.tactic_matchups, f"{mine.value}_vs_{theirs.value}_pct")) / PERCENT
