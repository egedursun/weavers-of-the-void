import asyncio
import logging
from collections.abc import Callable

from aerona.constants.limits import LIVE_LOG_PRUNE_EVERY
from aerona.events.bus import Event, EventBus
from aerona.events.kinds import UNSTORED_KINDS
from aerona.rules.registry import Rules
from aerona.services.metrics import MetricsService

logger = logging.getLogger(__name__)


class LiveLog:
    def __init__(self, bus: EventBus, metrics: MetricsService, rules: Callable[[], Rules]) -> None:
        self._bus = bus
        self._metrics = metrics
        self._rules = rules
        self._pending: list[Event] = []
        self._writes = 0
        self._task: asyncio.Task[None] | None = None

    async def restore(self) -> int:
        flow = self._rules().epoch_flow
        self._bus.set_capacity(flow.live_log_memory)
        events = await self._metrics.load_events(flow.live_log_memory)
        self._bus.restore(events)
        return len(events)

    def attach(self) -> None:
        self._bus.add_listener(self.enqueue)

    def enqueue(self, event: Event) -> None:
        if event.kind in UNSTORED_KINDS:
            return
        self._pending.append(event)
        if self._task is None or self._task.done():
            try:
                self._task = asyncio.get_running_loop().create_task(self.flush())
            except RuntimeError:
                self._pending.clear()

    async def flush(self) -> None:
        while self._pending:
            batch, self._pending = self._pending, []
            try:
                await self._metrics.record_events(batch)
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
