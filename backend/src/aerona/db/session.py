import asyncio
import multiprocessing
import threading
from collections import deque
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from aerona.constants.maintenance import SQLITE_CACHE_KIB, SQLITE_MMAP_BYTES
from aerona.constants.timeouts import SQLITE_BUSY_TIMEOUT_MS
from aerona.db.activity import install_activity_capture
from aerona.db.bond_index import drop_lookup
from aerona.db.book_marks import BookMarks, renew_past
from aerona.db.cascades import install_cascade_following
from aerona.db.fast_session import FastSession
from aerona.db.flush_batch import install_flush_batching
from aerona.db.inline_sqlite import inline_engine, threaded_engine
from aerona.db.key_moves import install_key_guard
from aerona.db.ledger_capture import install_change_capture
from aerona.db.ordered_reads import install_ordered_reads
from aerona.db.read_memo import KEEP_KEY, forget_all
from aerona.db.read_only import install_read_only_guard, mark_read_only


@dataclass(frozen=True)
class SharedGate:
    lock: Any
    wanting: Any
    generation: Any
    stop: Any
    book_generation: Any


def shared_gate() -> SharedGate:
    context = multiprocessing.get_context("spawn")
    return SharedGate(context.Lock(), context.Value("i", 0), context.Value("q", 0), context.Event(), context.Value("q", 0))


SHARED_PAUSE = 0.002


class WriteGate:
    def __init__(self, shared: SharedGate | None = None, *, yielding: bool = False) -> None:
        self._mutex = threading.Lock()
        self._held = False
        self._waiters: deque[tuple[asyncio.AbstractEventLoop, asyncio.Future[None]]] = deque()
        self._generation = 0
        self._book_generation = 0
        self._shared_taken = False
        self.shared = shared
        self.yielding = yielding

    @property
    def generation(self) -> int:
        return int(self.shared.generation.value) if self.shared is not None else self._generation

    @generation.setter
    def generation(self, value: int) -> None:
        self._generation = value
        if self.shared is not None:
            self.shared.generation.value = value

    @property
    def book_generation(self) -> int:
        return int(self.shared.book_generation.value) if self.shared is not None else self._book_generation

    @book_generation.setter
    def book_generation(self, value: int) -> None:
        self._book_generation = value
        if self.shared is not None:
            self.shared.book_generation.value = value

    def share(self, shared: SharedGate) -> None:
        shared.generation.value = self._generation
        shared.book_generation.value = self._book_generation
        self.shared = shared

    async def acquire(self) -> None:
        await self._acquire_here()
        try:
            await self._acquire_shared()
        except BaseException:
            self._release_here()
            raise

    async def _acquire_shared(self) -> None:
        shared = self.shared
        if shared is None:
            return
        if not self.yielding:
            with shared.wanting.get_lock():
                shared.wanting.value += 1
        try:
            while True:
                if self._try_shared(shared):
                    break
                await asyncio.sleep(SHARED_PAUSE)
        finally:
            if not self.yielding:
                with shared.wanting.get_lock():
                    shared.wanting.value -= 1
        self._shared_taken = True

    def _try_shared(self, shared: SharedGate) -> bool:
        if self.yielding and shared.wanting.value > 0:
            return False
        if not shared.lock.acquire(False):
            return False
        if self.yielding and shared.wanting.value > 0:
            shared.lock.release()
            return False
        return True

    async def _acquire_here(self) -> None:
        loop = asyncio.get_running_loop()
        with self._mutex:
            if not self._held and not self._waiters:
                self._held = True
                return
            waiter: asyncio.Future[None] = loop.create_future()
            self._waiters.append((loop, waiter))
        try:
            await waiter
        except asyncio.CancelledError:
            with self._mutex:
                queued = (loop, waiter) in self._waiters
                if queued:
                    self._waiters.remove((loop, waiter))
            if not queued and waiter.done() and not waiter.cancelled():
                self._release_here()
            raise

    def release(self) -> None:
        if self._shared_taken and self.shared is not None:
            self._shared_taken = False
            self.shared.lock.release()
        self._release_here()

    def _release_here(self) -> None:
        with self._mutex:
            while self._waiters:
                loop, waiter = self._waiters.popleft()
                if loop.is_closed():
                    continue
                loop.call_soon_threadsafe(self._hand, waiter)
                return
            self._held = False

    def _hand(self, waiter: asyncio.Future[None]) -> None:
        if waiter.done():
            self._release_here()
            return
        waiter.set_result(None)

    @asynccontextmanager
    async def held(self) -> AsyncIterator[None]:
        await self.acquire()
        try:
            yield
        finally:
            self.release()


class Database:
    def __init__(self, url: str, gate: WriteGate | None = None) -> None:
        self.url = url
        self.work_in_processes = False
        self.engine: AsyncEngine = inline_engine(url)
        self._sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=FastSession)
        self.threaded: AsyncEngine = threaded_engine(url, self.engine)
        self._threaded_sessions = async_sessionmaker(self.threaded, expire_on_commit=False, class_=FastSession)
        self.gate = gate or WriteGate()
        self.book_marks = BookMarks()
        for engine in {self.engine, self.threaded}:
            event.listen(engine.sync_engine, "connect", self._configure_connection)
            event.listen(engine.sync_engine, "begin", self._begin)
            event.listen(engine.sync_engine, "before_cursor_execute", self.book_marks.note)
        install_activity_capture()
        install_flush_batching()
        install_ordered_reads()
        install_read_only_guard()
        install_change_capture()
        install_cascade_following()
        install_key_guard()

    @property
    def generation(self) -> int:
        return self.gate.generation

    @generation.setter
    def generation(self, value: int) -> None:
        self.gate.generation = value

    @property
    def book_generation(self) -> int:
        return self.gate.book_generation

    def committed(self) -> None:
        self.generation += 1
        if self.book_marks.taken():
            self.gate.book_generation += 1
        if self.book_marks.past_taken():
            renew_past(self.url)

    def sibling(self) -> "Database":
        return Database(self.url, self.gate)

    async def close(self) -> None:
        await self.threaded.dispose()
        await self.engine.dispose()

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
    async def read_in_thread(self) -> AsyncIterator[AsyncSession]:
        async with self._threaded_sessions() as session:
            mark_read_only(session)
            yield session

    @asynccontextmanager
    async def write(self) -> AsyncIterator[AsyncSession]:
        async with self.gate.held():
            async with self._sessions() as session, session.begin():
                yield session
            self.committed()

    @asynccontextmanager
    async def steps(self) -> AsyncIterator["Steps"]:
        async with self._sessions() as session:
            yield Steps(self, session)

    async def dispose(self) -> None:
        await self.threaded.dispose()
        await self.engine.dispose()
        self.generation += 1
        self.gate.book_generation += 1

    async def replace_file(self, swap: Callable[[], None]) -> None:
        async with self.gate.held():
            await self.dispose()
            swap()
            renew_past(self.url)
            await self.dispose()


class Steps:
    def __init__(self, database: Database, session: AsyncSession) -> None:
        self.database = database
        self.session = session
        self.seen = database.generation
        session.sync_session.info[KEEP_KEY] = []

    @asynccontextmanager
    async def step(self) -> AsyncIterator[AsyncSession]:
        async with self.database.gate.held():
            if self.database.generation != self.seen:
                self.session.expire_all()
                forget_all(self.session.sync_session)
                drop_lookup(self.session.sync_session)
                self.session.sync_session.info[KEEP_KEY] = []
            async with self.session.begin():
                yield self.session
            self.database.committed()
            self.seen = self.database.generation
