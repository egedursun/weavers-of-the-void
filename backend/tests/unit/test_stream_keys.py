import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

SOURCE = """
async def sail(ctx, vessel, region_id: int | None):
    return ctx.rng(f"sail.{vessel.id}.{region_id}.{ctx.epoch}")


async def guarded(ctx, region_id: int | None):
    if region_id is None:
        return None
    return ctx.rng(f"sail.{region_id}")


async def worded(ctx, region_id: int | None):
    return ctx.rng(f"sail.{'adrift' if region_id is None else region_id}")


async def local(ctx):
    found: int | None = await pick(ctx)
    return ctx.rng(f"pick.{found}")
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_stream_keys", REPOSITORY_ROOT / "scripts" / "check_stream_keys.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_stream_keys"] = module
    spec.loader.exec_module(module)
    return module


def test_a_stream_keyed_by_a_value_that_may_be_missing_is_flagged() -> None:
    assert [item.line for item in checker().loose_keys({Path("module.py"): SOURCE})] == [3, 18]


def test_the_engine_keys_every_stream_by_a_present_value() -> None:
    module = checker()
    assert module.loose_keys({path: path.read_text(encoding="utf-8") for path in sorted(module.SOURCE.rglob("*.py"))}) == []
