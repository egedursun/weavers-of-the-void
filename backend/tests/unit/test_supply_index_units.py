import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

SOURCE = """
async def hoarded(ctx, town):
    food = await stock(ctx.session, ctx.rules, town.id, FOOD)
    return food * 100 / max(1, population_of(town)) < 30


async def petition(ctx, community):
    if await stock(ctx.session, ctx.rules, community.id, FOOD) < stat_or(community, "population", 0) * 1:
        return True


async def pressure(session, community, population):
    stocked = await stock(session, rules, community.id, FOOD)
    return max(stocked * 1000 / max(population, 1000), 0)


async def fair(ctx, town):
    food = await stock(ctx.session, ctx.rules, town.id, FOOD)
    taken = food * 30 // 100
    return food < ctx.rules.needs.hunger_food and taken < stat_or(town, "population", 0)


async def offer(ctx, community):
    gift = 40 * stat_or(community, "population", 0) / 1000
    await shift_stock(ctx.session, ctx.rules, community.id, FOOD, gift, epoch=1, flow=OFFERING)
    await shift_stock(ctx.session, ctx.rules, community.id, FOOD, 4, epoch=1, flow=OFFERING)
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_supply_index", REPOSITORY_ROOT / "scripts" / "check_supply_index.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_supply_index"] = module
    spec.loader.exec_module(module)
    return module


def test_a_supply_index_scaled_by_a_headcount_is_flagged() -> None:
    lines = sorted({item.line for item in checker().rescaled({Path("module.py"): SOURCE})})
    assert lines == [4, 8, 14, 20, 25]


def test_the_backend_never_scales_a_supply_index_by_a_headcount() -> None:
    module = checker()
    assert module.rescaled({path: path.read_text(encoding="utf-8") for path in sorted(module.SOURCE.rglob("*.py"))}) == []
