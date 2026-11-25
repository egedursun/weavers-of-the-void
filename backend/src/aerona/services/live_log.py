import asyncio
import logging
from collections.abc import Callable

from sqlalchemy import select

from aerona.constants.limits import LIVE_LOG_PRUNE_EVERY
from aerona.core.account_scope import detached
from aerona.db.session import Database
from aerona.db.tables.cosmos import CosmosRow
from aerona.events.bus import Event, EventBus
from aerona.events.kinds import UNSTORED_KINDS
from aerona.rules.registry import Rules
from aerona.services.metrics import MetricsService

logger = logging.getLogger(__name__)


async def world_key_of(database: Database) -> str | None:
    async with database.read() as session:
        found = (await session.execute(select(CosmosRow.rng_seed, CosmosRow.created_at).limit(1))).first()
    if found is None:
        return None
    seed, created = found
    return f"{seed}:{created.isoformat() if created is not None else ''}"


class LiveLog:
    def __init__(self, bus: EventBus, metrics: MetricsService, rules: Callable[[], Rules], database: Database) -> None:
        self._bus = bus
        self._metrics = metrics
        self._rules = rules
        self._database = database
        self._key: str | None = None
        self._pending: list[tuple[Event, str | None]] = []
        self._writes = 0
        self._task: asyncio.Task[None] | None = None

    async def restore(self) -> int:
        flow = self._rules().epoch_flow
        self._bus.set_capacity(flow.live_log_memory)
        self._key = await world_key_of(self._database)
        events = await self._metrics.load_events(flow.live_log_memory, self._key)
        self._bus.restore(events)
        return len(events)

    def attach(self) -> None:
        self._bus.add_listener(self.enqueue)

    def world_changed(self) -> None:
        self._bus.forget_history()
        self._key = None

    def enqueue(self, event: Event) -> None:
        if event.kind in UNSTORED_KINDS or event.audience is not None:
            return
        self._pending.append((event, self._key))
        if self._task is None or self._task.done():
            try:
                self._task = detached(self.flush())
            except RuntimeError:
                self._pending.clear()

    async def flush(self) -> None:
        while self._pending:
            batch, self._pending = self._pending, []
            try:
                current = await world_key_of(self._database)
                self._key = current
                owned: dict[str | None, list[Event]] = {}
                for event, key in batch:
                    owned.setdefault(key if key is not None else current, []).append(event)
                for key, events in owned.items():
                    await self._metrics.record_events(events, key)
                self._writes += len(batch)
                if self._writes >= LIVE_LOG_PRUNE_EVERY:
                    self._writes = 0
                    await self._metrics.prune_events(self._rules().epoch_flow.live_log_db)
            except Exception:
                logger.exception("live log write failed")

    async def drain(self) -> None:
        if self._task is not None:
            await self._task
        await self.flush()
