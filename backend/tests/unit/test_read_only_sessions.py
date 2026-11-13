from pathlib import Path

import pytest
from sqlalchemy import delete, func, select

from aerona.db.read_only import ReadSessionWriteError
from aerona.db.tables.entities import EntityFlagRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.engine.phases.doom import doom_forecast
from aerona.engine.phases.world_age import read_world_age
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.conftest import OpenDatabase
from tests.engine.integration import factories


async def test_a_read_session_refuses_every_write_so_no_reader_can_hold_the_write_lock(open_database: OpenDatabase, tmp_path: Path) -> None:
    database = open_database(tmp_path / "read.db")
    try:
        async with database.read() as session:
            session.add(ChronicleRow(epoch=1, kind=ChronicleKind.WORLD_AGE, text="Stray"))
            with pytest.raises(ReadSessionWriteError):
                await session.flush()
        async with database.read() as session:
            with pytest.raises(ReadSessionWriteError):
                await session.execute(delete(EntityFlagRow))
        async with database.write() as session:
            session.add(ChronicleRow(epoch=1, kind=ChronicleKind.WORLD_AGE, text="Kept"))
        async with database.read() as session:
            assert await session.scalar(select(func.count()).select_from(ChronicleRow).where(ChronicleRow.text == "Kept")) == 1
    finally:
        await database.dispose()


async def test_the_doom_forecast_and_the_age_of_worlds_only_read(open_database: OpenDatabase, tmp_path: Path) -> None:
    database = open_database(tmp_path / "doom.db")
    try:
        async with database.write() as session:
            await factories.seed_rich_cosmos(session)
        async with database.read() as session:
            rules = Rules()
            chronicle = await session.scalar(select(func.count()).select_from(ChronicleRow))
            forecast = await doom_forecast(session, rules)
            assert forecast.items
            reading = await read_world_age(await manual_context(session, "age_view", rules), 2)
            assert reading.verdicts
            assert await session.scalar(select(func.count()).select_from(ChronicleRow)) == chronicle
    finally:
        await database.dispose()
