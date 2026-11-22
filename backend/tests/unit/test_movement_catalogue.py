import importlib.util
from dataclasses import replace
from pathlib import Path
from types import ModuleType

from aerona.catalog.movement import MOVEMENT, by_water, trade_modes
from aerona.catalog.terrain import TERRAIN
from aerona.domain.enums.environment import CoastKind, MovementMedium, MovementMode, MovementWork, RiverClass, TerrainKind
from aerona.engine.environment.profile import Ground, Works, passability_of
from aerona.rules.registry import Rules
from aerona.rules.renames import canonical_overrides

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "check_movement_modes.py"
GROUND = Ground(roughness=40, forest=30, wetland=20, river=RiverClass.RIVER, temperature=5, coast=CoastKind.HARBOUR_SITE, terrain=TerrainKind.HILLS, tides=20)


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_movement_modes", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_terrain_has_a_passage_for_every_mode() -> None:
    rules = Rules()
    for kind, spec in TERRAIN.items():
        assert set(spec.passage(rules)) == set(MovementMode), kind


def test_passability_holds_a_value_for_every_mode() -> None:
    assert set(passability_of(Rules(), GROUND)) == {mode.value for mode in MovementMode}


def test_a_passage_key_changes_only_its_own_mode() -> None:
    rules = Rules()
    slower = replace(rules, passability=replace(rules.passability, hills_mounted_pct=40))
    before, after = passability_of(rules, GROUND), passability_of(slower, GROUND)
    assert after["mounted"] < before["mounted"]
    assert {mode: value for mode, value in after.items() if mode != "mounted"} == {mode: value for mode, value in before.items() if mode != "mounted"}


def test_works_help_only_the_modes_that_take_them() -> None:
    rules = Rules()
    bridged = replace(GROUND, works=Works(bridges=2))
    plain, crossed = passability_of(rules, GROUND), passability_of(rules, bridged)
    assert crossed["on_foot"] > plain["on_foot"]
    assert crossed["burrowing"] == plain["burrowing"]
    assert not MOVEMENT[MovementMode.BURROWING].takes(MovementWork.BRIDGES)


def test_the_medium_picks_the_water_and_trade_readers() -> None:
    assert by_water("boat") and not by_water("on_foot")
    assert MOVEMENT[MovementMode.FLYING].medium is MovementMedium.AIR
    assert trade_modes() == (MovementMode.ON_FOOT, MovementMode.WHEELED, MovementMode.BOAT)


def test_an_old_terrain_base_override_reaches_every_ground_passage() -> None:
    split = canonical_overrides({("passability", "marsh_base"): 60.0})
    assert split == {("passability", f"marsh_{mode}_pct"): 60.0 for mode in ("on_foot", "mounted", "wheeled", "burrowing")}


def test_a_special_case_of_a_mode_is_caught() -> None:
    text = "from aerona.domain.enums.environment import MovementMode as M\nboat = mode == M.BOAT.value\nLAND = (M.ON_FOOT, M.MOUNTED)\n"
    assert [item.line for item in checker().specials_in("engine/sample.py", text)] in ([2, 3], [3, 2])


def test_the_source_has_no_special_case_of_a_mode() -> None:
    assert checker().main() == 0
