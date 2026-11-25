import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from weakref import WeakKeyDictionary

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.account_scope import detached
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.db.session import Database
from aerona.events.bus import Event, EventBus
from aerona.events.kinds import EventKind
from aerona.rules.registry import Rules
from aerona.services.books.model import BookModel, build_book


@dataclass
class BookCache:
    generation: int | None = None
    model: BookModel | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


CACHES: WeakKeyDictionary[Database, BookCache] = WeakKeyDictionary()


def cache_of(database: Database) -> BookCache:
    found = CACHES.get(database)
    if found is None:
        found = CACHES[database] = BookCache()
    return found


async def cached_book(database: Database, session: AsyncSession, rules: Rules) -> BookModel | None:
    cache = cache_of(database)
    async with cache.lock:
        seen = database.generation
        if cache.generation != seen:
            cache.model = await build_book(session, rules)
            cache.generation = seen
        return cache.model


async def book_rules(session: AsyncSession, current: Rules) -> Rules:
    cosmos = await CosmosRepository(session).get()
    return rules_from_snapshot(cosmos.rules_snapshot) if cosmos is not None and cosmos.rules_snapshot else current


class BookWarmer:
    def __init__(self, bus: EventBus, database: Database, current: Callable[[], Rules], read_only: Callable[[], bool]) -> None:
        self._bus = bus
        self._database = database
        self._current = current
        self._read_only = read_only
        self._tasks: set[asyncio.Task[None]] = set()

    def attach(self) -> None:
        self._bus.add_listener(self.on_event)

    def on_event(self, event: Event) -> None:
        if event.kind is EventKind.EPOCH_FINISHED and not self._read_only():
            self._spawn(self.warm())

    def _spawn(self, work: Any) -> None:
        try:
            task = detached(work)
        except RuntimeError:
            work.close()
            return
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def warm(self) -> None:
        async with self._database.read() as session:
            await cached_book(self._database, session, await book_rules(session, self._current()))
