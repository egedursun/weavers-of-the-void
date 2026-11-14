import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_goods_ledger", REPOSITORY_ROOT / "scripts" / "check_goods_ledger.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_goods_ledger"] = module
    spec.loader.exec_module(module)
    return module


def test_a_stock_changed_by_hand_outside_the_ledger_is_caught() -> None:
    source = "lot.quantity -= taken\nstock.quantity += amount\nrow.quantity = total\ntaken = await ledger.take_units(town, kind, want, flow)\n"
    assert [item.line for item in checker().shifts({Path("engine/sample.py"): source})] == [1, 2]


def test_no_code_changes_a_stock_outside_the_ledger() -> None:
    module = checker()
    assert module.shifts(module.sources()) == []
