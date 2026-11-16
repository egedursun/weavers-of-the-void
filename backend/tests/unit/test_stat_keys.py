import importlib.util
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def guard() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_stat_keys", REPOSITORY_ROOT / "scripts" / "check_stat_keys.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_stat_no_thing_holds_is_found_and_a_held_one_passes() -> None:
    checker = guard()
    keys = checker.known_keys()
    assert "charisma" in keys
    assert checker.unknown_keys('stat_or(case.town, "loyalty", 50) and stat(row, "charisma")', keys) == ["loyalty"]
