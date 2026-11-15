import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

RAW = """
async def harvest_goods(ctx, book, community, rate):
    return scale_by_energy(book, community.id, kind, need)


async def mill_bread(ctx, book, community):
    return scale_by_energy(book, community.id, kind, need)


async def fishing_catch(ctx, book, community):
    return worked_by_hand(book, ctx.rules, community.id, kind, need=need, workers=workers)
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_food_energy", REPOSITORY_ROOT / "scripts" / "check_food_energy.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_food_energy"] = module
    spec.loader.exec_module(module)
    return module


def test_food_drawn_only_from_the_shared_pool_is_flagged() -> None:
    assert [item.function for item in checker().pooled_food({Path("module.py"): RAW})] == ["harvest_goods"]


def test_the_engine_lets_its_farmers_work_first() -> None:
    module = checker()
    assert module.pooled_food({path: path.read_text(encoding="utf-8") for path in sorted(module.SOURCE.rglob("*.py"))}) == []
