import importlib.util
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

LEVERS = """
async def veto(scope, command):
    spent = guards.charge(creator, scope.rules.council.veto_attention, "council.veto_attention")
    return spent


async def seat(scope, command):
    return None
"""

FREE_CATALOG = """
ACTIONS = (
    _sync(Meta("council:veto", "Veto a ruling", G.CREATOR), council.veto, council.VetoTarget, free, ()),
    _sync(Meta("seat:set", "Seat a god", G.CREATOR), council.seat, council.SeatSet, free, ()),
)
"""


def guard() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_lever_costs", REPOSITORY_ROOT / "scripts" / "check_lever_costs.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_lever_that_charges_essence_cannot_be_called_free(tmp_path: Path) -> None:
    checker = guard()
    (tmp_path / "council.py").write_text(LEVERS, encoding="utf-8")
    catalog = tmp_path / "catalog.py"
    catalog.write_text(FREE_CATALOG, encoding="utf-8")
    assert checker.mispriced(tmp_path, catalog) == [("council:veto", "council", "veto")]
    catalog.write_text(FREE_CATALOG.replace("council.VetoTarget, free", "council.VetoTarget, lambda rules: essence(5)"), encoding="utf-8")
    assert checker.mispriced(tmp_path, catalog) == []
