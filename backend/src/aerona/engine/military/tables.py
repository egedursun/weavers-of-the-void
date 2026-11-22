from aerona.catalog.terrain import TERRAIN
from aerona.catalog.units import TACTIC_COUNTERS
from aerona.catalog.weather import WEATHER
from aerona.constants.units import PERCENT
from aerona.domain.enums.environment import TerrainKind, WeatherKind
from aerona.domain.enums.military import Tactic, UnitFamily, UnitKind
from aerona.engine.military.rule_tables import tactic_matchup
from aerona.rules.registry import Rules


def terrain_cell(rules: Rules, terrain: TerrainKind | None, family: UnitFamily) -> float:
    if terrain is None:
        return 1.0
    return TERRAIN[terrain].unit_factors(rules).get(family, PERCENT) / PERCENT


def unit_terrain(rules: Rules, kind: UnitKind, terrain: TerrainKind | None) -> float:
    if terrain is None:
        return 1.0
    return TERRAIN[terrain].unit_kinds(rules).get(kind, PERCENT) / PERCENT


def defender_cell(rules: Rules, terrain: TerrainKind | None) -> float:
    if terrain is None:
        return 1.0
    return TERRAIN[terrain].defender(rules) / PERCENT


def weather_cell(rules: Rules, weather: WeatherKind | None, family: UnitFamily) -> float:
    if weather is None:
        return 1.0
    return WEATHER[weather].unit_factors(rules).get(family, PERCENT) / PERCENT


def counters(mine: Tactic, theirs: Tactic) -> bool:
    return theirs in TACTIC_COUNTERS.get(mine, frozenset())


def matchup(rules: Rules, mine: Tactic, theirs: Tactic) -> float:
    if not counters(mine, theirs):
        return 1.0
    return tactic_matchup(rules.tactic_matchups).get((mine.value, theirs.value), PERCENT) / PERCENT
