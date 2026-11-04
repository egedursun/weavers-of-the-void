from aerona.catalog.units import DEFENDER_TERRAIN, TACTIC_COUNTERS, TERRAIN_EFFECTS, WEATHER_EFFECTS
from aerona.constants.units import PERCENT
from aerona.domain.enums.environment import TerrainKind, WeatherKind
from aerona.domain.enums.military import Tactic, UnitFamily, UnitKind
from aerona.engine.military.rule_tables import kind_terrain, tactic_matchup, terrain_defender, terrain_family, weather_family
from aerona.rules.registry import Rules


def terrain_cell(rules: Rules, terrain: TerrainKind | None, family: UnitFamily) -> float:
    if terrain is None or family not in TERRAIN_EFFECTS.get(terrain, {}):
        return 1.0
    return terrain_family(rules.battle_terrain).get((terrain.value, family.value), PERCENT) / PERCENT


def unit_terrain(rules: Rules, kind: UnitKind, terrain: TerrainKind | None, affinities: dict[TerrainKind, float]) -> float:
    if terrain is None or terrain not in affinities:
        return 1.0
    found = kind_terrain(rules.battle_terrain).get((kind.value, terrain.value))
    return found / PERCENT if found is not None else affinities[terrain]


def defender_cell(rules: Rules, terrain: TerrainKind | None) -> float:
    if terrain is None or terrain not in DEFENDER_TERRAIN:
        return 1.0
    return terrain_defender(rules.battle_terrain).get(terrain.value, PERCENT) / PERCENT


def weather_cell(rules: Rules, weather: WeatherKind | None, family: UnitFamily) -> float:
    if weather is None or family not in WEATHER_EFFECTS.get(weather, {}):
        return 1.0
    return weather_family(rules.battle_weather).get((weather.value, family.value), PERCENT) / PERCENT


def counters(mine: Tactic, theirs: Tactic) -> bool:
    return theirs in TACTIC_COUNTERS.get(mine, frozenset())


def matchup(rules: Rules, mine: Tactic, theirs: Tactic) -> float:
    if not counters(mine, theirs):
        return 1.0
    return tactic_matchup(rules.tactic_matchups).get((mine.value, theirs.value), PERCENT) / PERCENT
