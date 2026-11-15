import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

SOURCE = """
def ambush(rows, table):
    for row in rows:
        row.morale = clamp_int(row.morale - table.ambush_morale, 0, PERCENT)


def shock(army, table):
    shift_stat(army, "morale", -table.standard_shock)


async def kept(ctx, army, rows, table):
    fear = await fear_of(ctx.session, army)
    for row in rows:
        row.morale = clamp_int(row.morale - round_half_up(table.ambush_morale * fear), 0, PERCENT)
    shift_stat(army, "morale", -table.standard_shock * await fear_of(ctx.session, army))
    shift_stat(army, "morale", table.rally)
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_morale_losses", REPOSITORY_ROOT / "scripts" / "check_morale_losses.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_morale_losses"] = module
    spec.loader.exec_module(module)
    return module


def test_a_morale_loss_that_ignores_the_body_is_flagged() -> None:
    assert sorted(item.line for item in checker().losses({Path("module.py"): SOURCE})) == [4, 8]


def test_every_morale_loss_in_the_backend_reads_the_fear_of_the_body() -> None:
    module = checker()
    assert module.losses({path: path.read_text(encoding="utf-8") for path in sorted(module.SOURCE.rglob("*.py"))}) == []
