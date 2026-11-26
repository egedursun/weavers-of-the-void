import asyncio
import threading
import time
from pathlib import Path

import pytest
from sqlalchemy import event, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from aerona.db.inline_sqlite import InlineConnection, ThreadedConnection
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


async def test_rows_read_in_one_step_stay_kept_for_the_next_and_are_let_go_after_a_foreign_write(tmp_path: Path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'keep.db'}")
    async with database.engine.begin() as connection:
        await connection.run_sync(ProbeBase.metadata.create_all)
    async with database.steps() as steps:
        async with steps.step() as session:
            session.add(Probe(id=1, value=1))
        async with steps.step() as session:
            await session.get(Probe, 1)
            first: list[object] = session.sync_session.info[KEEP_KEY]
            assert any(isinstance(row, Probe) for row in first)
        loads: list[object] = []
        event.listen(session.sync_session, "loaded_as_persistent", lambda _session, row: loads.append(row))
        async with steps.step() as session:
            assert session.sync_session.info[KEEP_KEY] is first
            assert (await session.scalars(select(Probe))).all() and not loads
        async with database.write() as other:
            row = await other.get(Probe, 1)
            assert row is not None
            row.value = 3
        async with steps.step() as session:
            assert session.sync_session.info[KEEP_KEY] is not first
            renewed = await session.get(Probe, 1)
            assert renewed is not None and renewed.value == 3
    await database.dispose()


async def test_reads_in_a_thread_run_sql_off_the_event_loop_and_see_committed_writes(tmp_path: Path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'threaded.db'}")
    async with database.engine.begin() as connection:
        await connection.execute(text("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)"))
    async with database.write() as session:
        await session.execute(text("INSERT INTO items (name) VALUES ('seen')"))
    loop_thread = threading.get_ident()
    threads: list[int] = []

    def thread_of() -> int:
        threads.append(threading.get_ident())
        return 1

    async with database.threaded.connect() as connection:
        raw = await connection.get_raw_connection()
        assert isinstance(raw.driver_connection, ThreadedConnection)
        raw.driver_connection.live.create_function("thread_of", 0, thread_of)
    async with database.read_in_thread() as session:
        names = (await session.execute(text("SELECT name FROM items WHERE thread_of() = 1 ORDER BY id"))).scalars().all()
        assert (await session.execute(text("PRAGMA foreign_keys"))).scalar() == 1
    assert names == ["seen"]
    assert threads and loop_thread not in threads
    await database.dispose()


async def test_a_slow_read_in_a_thread_leaves_the_event_loop_free(tmp_path: Path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'threaded.db'}")
    beats: list[int] = []

    async def heartbeat() -> None:
        while True:
            beats.append(1)
            await asyncio.sleep(0)

    def pause() -> int:
        time.sleep(0.2)
        return 1

    async with database.threaded.connect() as connection:
        raw = await connection.get_raw_connection()
        assert isinstance(raw.driver_connection, ThreadedConnection)
        raw.driver_connection.live.create_function("pause", 0, pause)
    pulse = asyncio.create_task(heartbeat())
    async with database.read_in_thread() as session:
        assert (await session.execute(text("SELECT pause()"))).scalar() == 1
    pulse.cancel()
    assert len(beats) > 10
    await database.dispose()


async def test_an_in_memory_database_reads_through_its_one_engine() -> None:
    database = Database("sqlite+aiosqlite:///:memory:")
    assert database.threaded is database.engine
    await database.dispose()
