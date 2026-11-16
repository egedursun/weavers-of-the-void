from pathlib import Path

from sqlalchemy import func, select

from aerona.db.session import Database
from aerona.db.tables.entities import EntityFlagRow, EntityRow, LanguageProfileRow
from aerona.db.tables.fossils import FossilBedRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.titles import TitleProfileRow
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.engine.prehistory.control import configure
from aerona.engine.prehistory.run import run_prehistory
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.conftest import OpenDatabase
from tests.engine.integration.factories import seed_rich_cosmos

EPOCHS = 40
RESOLUTION = 4


async def counted(database: Database) -> dict[str, object]:
    async with database.read() as session:
        families = [
            (row.entity_id, row.parent_language_id)
            for row in await session.scalars(select(LanguageProfileRow).where(LanguageProfileRow.parent_language_id.is_not(None)))
        ]
        cognates = 0
        for child, parent in families:
            mine = set(await session.scalars(select(LexemeRow.meaning).where(LexemeRow.language_entity_id == child)))
            theirs = set(await session.scalars(select(LexemeRow.meaning).where(LexemeRow.language_entity_id == parent)))
            cognates += len(mine & theirs)
        return {
            "languages": sorted(await session.scalars(select(EntityRow.name).where(EntityRow.entity_type == EntityType.LANGUAGE))),
            "families": len(families),
            "cognates": cognates,
            "ruins": await session.scalar(select(func.count()).select_from(EntityFlagRow).where(EntityFlagRow.flag == EntityFlag.RUIN)),
            "dormant": await session.scalar(
                select(func.count()).select_from(TitleProfileRow).where(TitleProfileRow.holder_node_id.is_(None), TitleProfileRow.destroyed_epoch.is_(None))
            ),
            "fossils": await session.scalar(select(func.count()).select_from(FossilBedRow)),
            "grudges": await session.scalar(select(func.count()).select_from(MemoryRow).where(MemoryRow.kind == MemoryKind.HARMED_ME)),
            "newest": await session.scalar(select(func.max(EntityRow.birth_epoch))),
        }


async def lived(database: Database) -> tuple[dict[str, object], dict[str, object], int]:
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        target = cosmos.home.world.id
        ctx = await manual_context(session, "prehistory_j18", Rules())
        birth = ctx.epoch
        await configure(ctx, target, EPOCHS, RESOLUTION)
    before = await counted(database)
    await run_prehistory(database, target)
    return before, await counted(database), birth


async def test_a_forty_epoch_prehistory_leaves_language_families_ruins_and_dormant_titles_the_same_for_the_same_seed(
    database: Database, tmp_path: Path, open_database: OpenDatabase
) -> None:
    before, after, birth = await lived(database)
    assert after["families"] > before["families"] and after["cognates"]
    assert after["ruins"] > before["ruins"] and after["dormant"]
    assert after["newest"] == birth
    twin = open_database(tmp_path / "twin.db")
    try:
        _, again, _ = await lived(twin)
    finally:
        await twin.dispose()
    assert again == after


async def test_story_30_the_kingdom_before_us(database: Database) -> None:
    before, after, birth = await lived(database)
    assert after["families"] > before["families"]
    assert after["ruins"] > before["ruins"]
    assert after["dormant"]
    assert after["fossils"]
    assert after["grudges"] > before["grudges"]
    assert after["newest"] == birth
