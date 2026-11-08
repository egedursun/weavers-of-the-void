import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

SOURCE = """
def hp(hero):
    return stat(hero, "hp") or 100


def wealth(town):
    return stat(town, "wealth") or stat(town, "prosperity") or 0


def near(atlas, first, second):
    return (atlas.region_hops(first, second) or 100) <= 1


def safe(hero, atlas, first, second):
    return (stat(hero, "hp") or 0) + (atlas.region_hops(first, second) or 0) + stat_or(hero, "hp", 100)
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_zero_fallbacks", REPOSITORY_ROOT / "scripts" / "check_zero_fallbacks.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_zero_fallbacks"] = module
    spec.loader.exec_module(module)
    return module


def test_a_zero_read_as_missing_is_flagged() -> None:
    assert [item.line for item in checker().fallbacks({Path("module.py"): SOURCE})] == [3, 7, 11]


def test_the_backend_never_reads_a_true_zero_as_missing() -> None:
    module = checker()
    assert module.fallbacks({path: path.read_text(encoding="utf-8") for path in sorted(module.SOURCE.rglob("*.py"))}) == []
