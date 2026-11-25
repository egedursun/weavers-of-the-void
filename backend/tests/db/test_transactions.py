import pytest
from sqlalchemy import func, select

from aerona.db.session import Database
from aerona.db.tables.divine_will import DivineWillSessionRow


class AbandonedError(Exception):
    pass


async def count(database: Database) -> int:
    async with database.read() as session:
        return int(await session.scalar(select(func.count()).select_from(DivineWillSessionRow)) or 0)


async def test_a_released_savepoint_is_undone_when_the_write_fails_after_it(database: Database) -> None:
    with pytest.raises(AbandonedError):
        async with database.write() as session:
            async with session.begin_nested():
                session.add(DivineWillSessionRow(title="kept only by a released savepoint", opened_epoch=1))
            raise AbandonedError
    assert await count(database) == 0


async def test_a_write_that_ends_well_keeps_what_its_savepoints_released(database: Database) -> None:
    async with database.write() as session, session.begin_nested():
        session.add(DivineWillSessionRow(title="kept", opened_epoch=1))
    assert await count(database) == 1


async def test_a_rolled_back_savepoint_spares_the_rest_of_the_write(database: Database) -> None:
    async with database.write() as session:
        session.add(DivineWillSessionRow(title="outer", opened_epoch=1))
        nested = await session.begin_nested()
        session.add(DivineWillSessionRow(title="inner", opened_epoch=1))
        await session.flush()
        await nested.rollback()
    assert await count(database) == 1
