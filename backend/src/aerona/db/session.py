import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from aerona.constants.maintenance import SQLITE_CACHE_KIB, SQLITE_MMAP_BYTES
from aerona.constants.timeouts import SQLITE_BUSY_TIMEOUT_MS
from aerona.db.activity import install_activity_capture
from aerona.db.bond_index import drop_lookup
from aerona.db.cascades import install_cascade_following
from aerona.db.fast_session import FastSession
from aerona.db.flush_batch import install_flush_batching
from aerona.db.inline_sqlite import inline_engine
from aerona.db.key_moves import install_key_guard
from aerona.db.ledger_capture import install_change_capture
from aerona.db.ordered_reads import install_ordered_reads
from aerona.db.read_memo import KEEP_KEY, forget_all
from aerona.db.read_only import install_read_only_guard, mark_read_only


class Database:
    def __init__(self, url: str) -> None:
        self.engine: AsyncEngine = inline_engine(url)
        self._sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=FastSession)
        self._write_lock = asyncio.Lock()
        self.generation = 0
        event.listen(self.engine.sync_engine, "connect", self._configure_connection)
        event.listen(self.engine.sync_engine, "begin", self._begin)
        install_activity_capture()
        install_flush_batching()
        install_ordered_reads()
        install_read_only_guard()
        install_change_capture()
        install_cascade_following()
        install_key_guard()

    @staticmethod
    def _configure_connection(connection: Any, _record: Any) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA trusted_schema=OFF")
        cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
        cursor.execute(f"PRAGMA cache_size=-{SQLITE_CACHE_KIB}")
        cursor.execute(f"PRAGMA mmap_size={SQLITE_MMAP_BYTES}")
        cursor.close()
        connection.isolation_level = None

    @staticmethod
    def _begin(connection: Any) -> None:
        connection.exec_driver_sql("BEGIN")

    @asynccontextmanager
    async def read(self) -> AsyncIterator[AsyncSession]:
        async with self._sessions() as session:
            mark_read_only(session)
            yield session

    @asynccontextmanager
    async def write(self) -> AsyncIterator[AsyncSession]:
        async with self._write_lock:
            async with self._sessions() as session, session.begin():
                yield session
            self.generation += 1

    @asynccontextmanager
    async def steps(self) -> AsyncIterator["Steps"]:
        async with self._sessions() as session:
            yield Steps(self, session)

    async def dispose(self) -> None:
        await self.engine.dispose()
        self.generation += 1

    async def replace_file(self, swap: Callable[[], None]) -> None:
        async with self._write_lock:
            await self.dispose()
            swap()
            await self.dispose()


class Steps:
    def __init__(self, database: Database, session: AsyncSession) -> None:
        self.database = database
        self.session = session
        self.seen = database.generation
        session.sync_session.info[KEEP_KEY] = []

    @asynccontextmanager
    async def step(self) -> AsyncIterator[AsyncSession]:
        async with self.database._write_lock:
            if self.database.generation != self.seen:
                self.session.expire_all()
                forget_all(self.session.sync_session)
                drop_lookup(self.session.sync_session)
                self.session.sync_session.info[KEEP_KEY] = []
            async with self.session.begin():
                yield self.session
            self.database.generation += 1
            self.seen = self.database.generation
