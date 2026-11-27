from types import SimpleNamespace
from typing import cast

from aerona.domain.enums.environment import TerrainKind
from aerona.domain.enums.world_view import SettleMode, WarTerrain
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.routes import over_water
from aerona.engine.environment.battleground import war_ground
from aerona.engine.settlement.modes import SettleScene, chosen, fits
from aerona.rules.registry import Rules
from aerona.services.books.citysvg import walls_fact

RULES = Rules()


def test_a_battle_is_fought_at_sea_only_on_open_water_and_on_land_everywhere_else() -> None:
    assert war_ground(WarTerrain.NAVAL, TerrainKind.RUIN_FIELD) is WarTerrain.LAND
    assert war_ground(WarTerrain.LAND, TerrainKind.SEA) is WarTerrain.NAVAL
    assert war_ground(WarTerrain.NAVAL, TerrainKind.SEA) is WarTerrain.NAVAL
    assert war_ground(WarTerrain.LAND, TerrainKind.PLAIN) is WarTerrain.LAND


def test_a_town_on_open_water_never_stands_on_the_ground_or_on_cliffs() -> None:
    scene = SettleScene(None, frozenset(), TerrainKind.SEA, 0, SettleMode.CLIFF)
    assert not fits(RULES, SettleMode.CLIFF, scene)
    assert not fits(RULES, SettleMode.GROUND, scene)
    mode = chosen(RULES, scene)
    assert fits(RULES, mode, scene) and mode is not SettleMode.CLIFF
    ashore = SettleScene(None, frozenset(), TerrainKind.PLAIN, 0, SettleMode.CLIFF)
    assert chosen(RULES, ashore) is SettleMode.CLIFF


def test_a_route_whose_every_land_is_open_water_is_sailed() -> None:
    grounds = {1: SimpleNamespace(dominant_terrain=TerrainKind.SEA), 2: SimpleNamespace(dominant_terrain=TerrainKind.PLAIN)}
    book = cast(EconomyBook, SimpleNamespace(ground=SimpleNamespace(regions=grounds)))
    assert over_water(book, [1])
    assert not over_water(book, [1, 2])
    assert not over_water(book, [2])


def test_a_town_plan_never_calls_walls_that_stand_none() -> None:
    assert walls_fact(0, None) == "none"
    assert walls_fact(5, None) == "level 5, close around the town"
    assert walls_fact(3, 2) == "level 3, 2 hexes out"
