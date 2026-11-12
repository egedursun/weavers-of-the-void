import asyncio
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from aerona.db.inline_sqlite import InlineConnection
from aerona.db.read_memo import KEEP_KEY
from aerona.db.session import Database


class ProbeBase(DeclarativeBase):
    pass


class Probe(ProbeBase):
    __tablename__ = "probe"

    id: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[int]


async def test_the_database_talks_to_sqlite_inline_without_a_driver_thread(tmp_path: Path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'inline.db'}")
    async with database.engine.connect() as connection:
        raw = await connection.get_raw_connection()
        assert isinstance(raw.driver_connection, InlineConnection)
        assert (await connection.execute(text("PRAGMA foreign_keys"))).scalar() == 1
    await database.dispose()


async def test_inline_transactions_commit_roll_back_and_raise_integrity_errors(tmp_path: Path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'inline.db'}")
    async with database.engine.begin() as connection:
        await connection.execute(text("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT UNIQUE)"))
        await connection.execute(text("INSERT INTO items (name) VALUES ('kept')"))
    with pytest.raises(IntegrityError):
        async with database.engine.begin() as connection:
            await connection.execute(text("INSERT INTO items (name) VALUES ('lost')"))
            await connection.execute(text("INSERT INTO items (name) VALUES ('kept')"))
    async with database.engine.connect() as connection:
        names = (await connection.execute(text("SELECT name FROM items ORDER BY id"))).scalars().all()
    assert names == ["kept"]
    await database.dispose()


async def test_a_long_run_of_inline_queries_lets_other_tasks_run(tmp_path: Path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'inline.db'}")
    beats: list[int] = []

    async def heartbeat() -> None:
        while True:
            beats.append(1)
            await asyncio.sleep(0)

    pulse = asyncio.create_task(heartbeat())
    async with database.engine.connect() as connection:
        for _ in range(1000):
            await connection.execute(text("SELECT 1"))
    pulse.cancel()
    assert len(beats) > 1
    await database.dispose()


async def test_steps_keep_one_session_and_reload_after_a_foreign_write(tmp_path: Path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'steps.db'}")
    async with database.engine.begin() as connection:
        await connection.run_sync(ProbeBase.metadata.create_all)
    async with database.steps() as steps:
        async with steps.step() as session:
            session.add(Probe(id=1, value=1))
        async with steps.step() as session:
            kept = await session.get(Probe, 1)
            assert kept is not None and kept.value == 1
        async with database.write() as other:
            row = await other.get(Probe, 1)
            assert row is not None
            row.value = 2
        async with steps.step() as session:
            fresh = await session.get(Probe, 1)
            assert fresh is kept and fresh is not None and fresh.value == 2
    await database.dispose()


async def test_each_step_starts_a_fresh_keep_list_so_old_rows_can_be_freed(tmp_path: Path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'keep.db'}")
    async with database.engine.begin() as connection:
        await connection.run_sync(ProbeBase.metadata.create_all)
    async with database.steps() as steps:
        async with steps.step() as session:
            session.add(Probe(id=1, value=1))
        async with steps.step() as session:
            await session.get(Probe, 1)
            first: list[object] = session.sync_session.info[KEEP_KEY]
        async with steps.step() as session:
            second: list[object] = session.sync_session.info[KEEP_KEY]
            assert second is not first and second == []
    await database.dispose()
