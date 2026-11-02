import asyncio

import pytest
from sqlalchemy import func, select

from aerona.db.session import Database
from aerona.db.tables.celestial import WorldRow
from tests.db.factories import seed_world


class UnitFailedError(Exception):
    pass


async def world_count(database: Database) -> int:
    async with database.read() as session:
        return int(await session.scalar(select(func.count()).select_from(WorldRow)) or 0)


async def test_a_failing_write_unit_rolls_back_everything_it_wrote(database: Database) -> None:
    with pytest.raises(UnitFailedError):
        async with database.write() as session:
            await seed_world(session)
            raise UnitFailedError
    assert await world_count(database) == 0


async def test_write_units_never_join_and_run_one_after_another(database: Database) -> None:
    order: list[str] = []
    first_open = asyncio.Event()

    async def first() -> None:
        async with database.write() as session:
            order.append("first start")
            first_open.set()
            await asyncio.sleep(0.05)
            await seed_world(session)
            order.append("first end")

    async def second() -> None:
        await first_open.wait()
        async with database.write():
            order.append("second start")

    await asyncio.gather(first(), second())
    assert order == ["first start", "first end", "second start"]
    assert await world_count(database) == 1
