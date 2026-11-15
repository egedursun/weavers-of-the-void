import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

RAW = """
async def folk_of_town(session, town):
    return await session.get(EntityRow, town.affiliated_entity_id)


async def towns(session, people):
    return await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.affiliated_entity_id == people.id))


async def homes(session, people_id):
    return await session.scalars(select(EntityRow.id).where(EntityRow.affiliated_entity_id == people_id))


async def soldiers(session, people_id):
    return await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.affiliated_entity_id == people_id))


async def resolved(session, town):
    return await people_of(session, town)
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_town_people", REPOSITORY_ROOT / "scripts" / "check_town_people.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_town_people"] = module
    spec.loader.exec_module(module)
    return module


def test_a_town_read_as_holding_its_people_by_affiliation_is_flagged() -> None:
    found = checker().raw_links({Path("module.py"): RAW})
    assert [item.line for item in found] == [3, 7, 11]


def test_the_backend_finds_a_town_s_people_only_through_its_homeland() -> None:
    module = checker()
    assert module.raw_links({path: path.read_text(encoding="utf-8") for path in sorted(module.SOURCE.rglob("*.py"))}) == []
