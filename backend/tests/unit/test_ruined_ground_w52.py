from aerona.catalog.terrain import terrains
from aerona.domain.enums.economy import ExtractionKind
from aerona.domain.enums.environment import TerrainKind, TerrainTrait
from aerona.engine.belonging.sanctuary import HIDING
from aerona.engine.economy.extraction import FROM_RUINS, RUINS
from aerona.rules.registry import Rules


def test_a_ruin_field_is_ruined_ground_where_fugitives_hide_and_quarries_take_dressed_stone() -> None:
    assert terrains(TerrainTrait.RUINED) == {TerrainKind.RUIN_FIELD} == RUINS
    assert TerrainKind.RUIN_FIELD in HIDING
    assert {ExtractionKind.QUARRYING, ExtractionKind.SALVAGE} == FROM_RUINS
    assert Rules().ruined_ground.stone_pct > 0
