import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from aerona.constants.timeouts import SQLITE_BUSY_TIMEOUT_MS
from aerona.db.activity import install_activity_capture
from aerona.db.bond_index import drop_lookup
from aerona.db.fast_session import FastSession
from aerona.db.flush_batch import install_flush_batching
from aerona.db.inline_sqlite import inline_engine
from aerona.db.read_memo import KEEP_KEY, forget_all
from aerona.db.read_only import install_read_only_guard, mark_read_only


class Database:
    def __init__(self, url: str) -> None:
        self.engine: AsyncEngine = inline_engine(url)
        self._sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=FastSession)
        self._write_lock = asyncio.Lock()
        self.generation = 0
        event.listen(self.engine.sync_engine, "connect", self._configure_connection)
        install_activity_capture()
        install_flush_batching()
        install_read_only_guard()

    @staticmethod
    def _configure_connection(connection: Any, _record: Any) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA trusted_schema=OFF")
        cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
        cursor.close()

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
