import asyncio
from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.account_scope import detached
from aerona.db.repositories.cosmos import CosmosRepository, rules_from_snapshot
from aerona.db.session import Database
from aerona.events.bus import Event, EventBus
from aerona.events.kinds import EventKind
from aerona.rules.registry import Rules
from aerona.services.books import write_book_parts
from aerona.services.books.render import ScreenLinks
from aerona.settings import Settings


async def book_rules(session: AsyncSession, current: Rules) -> Rules:
    cosmos = await CosmosRepository(session).get()
    return rules_from_snapshot(cosmos.rules_snapshot) if cosmos is not None and cosmos.rules_snapshot else current


class BookWarmer:
    def __init__(self, bus: EventBus, database: Database, current: Callable[[], Rules], read_only: Callable[[], bool], settings: Settings) -> None:
        self._settings = settings
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
            rules = await book_rules(session, self._current())
            await write_book_parts(self._database, session, rules, ScreenLinks(universe=self._settings.universe_id or None), self._settings)
