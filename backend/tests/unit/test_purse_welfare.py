import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

RAW = """
def poverty(town):
    return stat_or(town, "wealth", stat(town, "prosperity") or 0)


def loot(town):
    return riches_of(town)


def lot(town):
    return stat(town, "prosperity") or 0


def purse(town):
    return stat_or(town, "wealth", 0)
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_purse_welfare", REPOSITORY_ROOT / "scripts" / "check_purse_welfare.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_purse_welfare"] = module
    spec.loader.exec_module(module)
    return module


def test_a_purse_read_with_prosperity_as_its_fallback_is_flagged() -> None:
    assert [item.line for item in checker().purse_blends({Path("module.py"): RAW})] == [3]


def test_the_backend_never_reads_a_purse_as_welfare() -> None:
    module = checker()
    assert module.purse_blends({path: path.read_text(encoding="utf-8") for path in sorted(module.SOURCE.rglob("*.py"))}) == []
