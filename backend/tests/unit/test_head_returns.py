import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

RAW = """
def returned(rules, town, count):
    before = headcount(town)
    after = put_stat(rules, town, headcount_key(town), before + count)
    return after - before


def grown(rules, town, born):
    put_stat(rules, town, headcount_key(town), headcount(town) + born)
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_head_returns", REPOSITORY_ROOT / "scripts" / "check_head_returns.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_head_returns"] = module
    spec.loader.exec_module(module)
    return module


def test_heads_counted_by_hand_after_a_headcount_is_set_are_flagged() -> None:
    found = checker().raw_returns({Path("module.py"): RAW})
    assert [item.line for item in found] == [4]


def test_the_backend_counts_returned_heads_only_through_the_levy_primitives() -> None:
    module = checker()
    assert module.raw_returns({path: path.read_text(encoding="utf-8") for path in sorted(module.SOURCE.rglob("*.py"))}) == []
