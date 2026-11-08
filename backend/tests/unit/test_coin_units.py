import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

RULES = """
class Table:
    pay: int = rule(6, 0, 100, W, "Treasury a hundred soldiers ask in a season")
    dues: int = rule(1, 0, 100, W, "Treasury per ten points of wealth")
    fee: int = rule(5, 0, 100, W, "Wealth a licensee pays")
"""

ENGINE = """
def raw(rules, payer):
    shift_stat(payer, "wealth", -rules.table.pay)


def converted(rules, payer):
    shift_stat(payer, "wealth", -wealth_points(rules, rules.table.pay))


def points(rules, payer):
    shift_stat(payer, "wealth", -rules.table.fee - rules.table.dues)
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_coin_units", REPOSITORY_ROOT / "scripts" / "check_coin_units.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_coin_units"] = module
    spec.loader.exec_module(module)
    return module


def test_treasury_spent_as_wealth_points_is_flagged() -> None:
    module = checker()
    fields = module.treasury_fields([RULES])
    assert fields == frozenset({"pay"})
    assert [(item.line, item.field) for item in module.mixed_units({Path("module.py"): ENGINE}, fields)] == [(3, "pay")]


def test_the_engine_converts_every_treasury_amount_it_spends_as_wealth() -> None:
    module = checker()
    fields = module.treasury_fields([path.read_text(encoding="utf-8") for path in sorted(module.RULES.rglob("*.py"))])
    assert module.mixed_units({path: path.read_text(encoding="utf-8") for path in sorted(module.ENGINE.rglob("*.py"))}, fields) == []
