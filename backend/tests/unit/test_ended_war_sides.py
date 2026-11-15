import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

RAW = """
async def after_wars(ctx):
    for war in await ctx.session.scalars(select(WarRow).where(WarRow.ended_epoch.in_([ctx.epoch - 1, ctx.epoch]))):
        for side in await war_sides(ctx.session, war.id):
            yield side


async def finished(ctx):
    for war in await ctx.session.scalars(select(WarRow).where(WarRow.ended_epoch >= ctx.epoch)):
        yield await standing_sides(ctx.session, war.id)


async def ongoing(ctx):
    for war in await ctx.session.scalars(select(WarRow).where(WarRow.ended_epoch.is_(None))):
        yield await war_sides(ctx.session, war.id)


async def remembered(ctx):
    for war in await ctx.session.scalars(select(WarRow).where(WarRow.ended_epoch == ctx.epoch)):
        yield await every_side(ctx.session, war.id)
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_ended_war_sides", REPOSITORY_ROOT / "scripts" / "check_ended_war_sides.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_ended_war_sides"] = module
    spec.loader.exec_module(module)
    return module


def test_ended_wars_read_through_the_sides_still_fighting_are_flagged() -> None:
    found = checker().standing_reads({Path("module.py"): RAW})
    assert [(item.line, item.function) for item in found] == [(4, "after_wars"), (10, "finished")]


def test_the_backend_reads_ended_wars_through_every_side() -> None:
    module = checker()
    assert module.standing_reads({path: path.read_text(encoding="utf-8") for path in sorted(module.SOURCE.rglob("*.py"))}) == []
