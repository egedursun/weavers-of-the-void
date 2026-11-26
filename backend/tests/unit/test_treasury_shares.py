import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

SOURCE = """
def demand(realm, pct):
    return realm.treasury * pct // 100


def drain(realm, wanted):
    return min(realm.treasury, wanted)


def tithe(town):
    return round(town.profile.treasury / 10)


def safe(realm, wanted, pct):
    return min(held_coin(realm.treasury), wanted) + held_coin(realm.treasury) * pct + max(1, realm.treasury) + realm.treasury - wanted
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_treasury_shares", REPOSITORY_ROOT / "scripts" / "check_treasury_shares.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_treasury_shares"] = module
    spec.loader.exec_module(module)
    return module


def test_a_share_of_a_treasury_in_debt_is_flagged() -> None:
    assert sorted(item.line for item in checker().shares({Path("module.py"): SOURCE})) == [3, 7, 11]


def test_the_backend_takes_every_treasury_share_through_held_coin() -> None:
    module = checker()
    assert module.shares({path: path.read_text(encoding="utf-8") for path in sorted(module.SOURCE.rglob("*.py"))}) == []
