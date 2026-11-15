import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

RAW = """
async def wager(ctx, town, club):
    wealth = stat_or(town, "wealth", 0)
    stake = round_half_up(wealth * ctx.rules.sports.stake_pct / PERCENT)
    return stake


async def fee_of(ctx, town):
    fee = stat(town, "prosperity") * ctx.rules.tolls.rate_pct // PERCENT
    return fee


async def coin_stake(ctx, town):
    stake = round_half_up(await coin_of(ctx.session, ctx.rules, town) * ctx.rules.sports.stake_pct / PERCENT)
    return stake
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_point_shares", REPOSITORY_ROOT / "scripts" / "check_point_shares.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_point_shares"] = module
    spec.loader.exec_module(module)
    return module


def test_an_amount_taken_as_a_share_of_a_point_stat_is_flagged() -> None:
    found = checker().raw_shares({Path("module.py"): RAW})
    assert [item.line for item in found] == [4, 9]


def test_the_backend_takes_amounts_of_coin_only_from_coin() -> None:
    module = checker()
    assert module.raw_shares({path: path.read_text(encoding="utf-8") for path in sorted(module.SOURCE.rglob("*.py"))}) == []
