import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

SOURCE = """
def year_of(world):
    return world.orbit * 2


def year_of_planet(world, worlds):
    return root_of(worlds, world).orbit * 2


def tide(moon):
    return moon.orbit


def warmth(world):
    if world.parent_world_id is not None:
        return 0
    return world.orbit
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_moon_orbits", REPOSITORY_ROOT / "scripts" / "check_moon_orbits.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_moon_orbits"] = module
    spec.loader.exec_module(module)
    return module


def test_an_orbit_read_that_cannot_tell_a_moon_from_a_planet_is_flagged() -> None:
    found = checker().reads({Path("module.py"): SOURCE})
    assert [(item.line, item.function) for item in found] == [(3, "year_of")]


def test_no_engine_reads_a_moons_orbit_as_its_distance_from_its_star() -> None:
    module = checker()
    assert module.reads(module.sources()) == []
