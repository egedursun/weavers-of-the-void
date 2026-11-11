import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

RAW = """
async def townsfolk(session, town):
    return await session.scalars(select(EntityRow).where(EntityRow.location_id == town.id, EntityRow.entity_type == EntityType.MORTAL))


async def realmfolk(session, towns):
    return await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.location_id.in_(towns)))


async def buildings(session, town):
    return await session.scalars(select(EntityRow).where(EntityRow.location_id == town.id, EntityRow.entity_type == EntityType.STRUCTURE))


async def merchants(session, town):
    return await session.scalars(select(EntityRow).where(EntityRow.location_id == town.id, EntityRow.mortal_role == MortalRole.MERCHANT))


async def folk(session, town):
    return await session.scalars(select(EntityRow).where(await present_among(session, [town.id]), EntityRow.entity_type == EntityType.MORTAL))
"""


def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_folk_queries", REPOSITORY_ROOT / "scripts" / "check_folk_queries.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_folk_queries"] = module
    spec.loader.exec_module(module)
    return module


def test_mortals_found_by_a_raw_place_are_flagged() -> None:
    found = checker().raw_queries({Path("module.py"): RAW})
    assert [item.line for item in found] == [3, 7, 15]


def test_the_backend_finds_mortals_of_a_place_only_through_the_folk_primitives() -> None:
    module = checker()
    assert module.raw_queries({path: path.read_text(encoding="utf-8") for path in sorted(module.SOURCE.rglob("*.py"))}) == []
