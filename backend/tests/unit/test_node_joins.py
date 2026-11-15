import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

SOURCE = """
async def bad(session):
    return await session.execute(select(EntityRow, WorldRow).join(WorldRow, WorldRow.id == EntityRow.world_id))


async def good(session):
    world = aliased(WorldRow, flat=True)
    rows = await session.execute(select(EntityRow, world).join(world, world.id == EntityRow.world_id))
    return await session.execute(select(WorldRow.name, WorldEndRow.state).join(WorldEndRow, WorldEndRow.world_id == WorldRow.id)), rows
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_node_joins", REPOSITORY_ROOT / "scripts" / "check_node_joins.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_node_joins"] = module
    spec.loader.exec_module(module)
    return module


def test_a_join_of_two_kinds_of_node_without_an_alias_is_flagged() -> None:
    assert [item.line for item in checker().joins({Path("module.py"): SOURCE})] == [3]


def test_the_backend_never_joins_two_kinds_of_node_without_an_alias() -> None:
    module = checker()
    assert module.joins({path: path.read_text(encoding="utf-8") for path in sorted(module.SOURCE.rglob("*.py"))}) == []
