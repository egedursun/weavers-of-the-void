import asyncio
from collections import deque
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from aerona.constants.limits import EVENT_REPLAY_BUFFER_SIZE, EVENT_SUBSCRIBER_QUEUE_SIZE
from aerona.events.kinds import EPOCH_TRACKING_KINDS, TRANSIENT_KINDS, EventKind


@dataclass(frozen=True)
class Event:
    id: int
    kind: EventKind
    payload: dict[str, Any]
    at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def as_json(self) -> dict[str, Any]:
        return {"id": self.id, "kind": self.kind.value, "payload": self.payload, "at": self.at.isoformat()}


class EventBus:
    def __init__(self, replay_size: int = EVENT_REPLAY_BUFFER_SIZE) -> None:
        self._sequence = 0
        self._history: deque[Event] = deque(maxlen=replay_size)
        self._subscribers: set[asyncio.Queue[Event]] = set()
        self._listeners: list[Callable[[Event], None]] = []
        self._epoch: int | None = None

    @property
    def epoch(self) -> int | None:
        return self._epoch

    def set_epoch(self, epoch: int | None) -> None:
        self._epoch = epoch

    def add_listener(self, listener: Callable[[Event], None]) -> None:
        self._listeners.append(listener)

    def set_capacity(self, size: int) -> None:
        self._history = deque(self._history, maxlen=size)

    def forget_history(self) -> None:
        self._history.clear()

    def restore(self, events: list[Event]) -> None:
        for item in events:
            self._history.append(item)
            self._sequence = max(self._sequence, item.id)

    def observe_epoch(self, kind: EventKind, payload: dict[str, Any]) -> None:
        if kind not in EPOCH_TRACKING_KINDS:
            return
        value = payload.get("new_epoch") if kind is EventKind.EPOCH_FINISHED else payload.get("epoch")
        if isinstance(value, int):
            self._epoch = value

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    @property
    def last_id(self) -> int:
        return self._sequence

    def publish(self, kind: EventKind, payload: dict[str, Any] | None = None) -> Event:
        self._sequence += 1
        body = dict(payload or {})
        if body.get("epoch") is None and self._epoch is not None:
            body["epoch"] = self._epoch
        self.observe_epoch(kind, body)
        published = Event(id=self._sequence, kind=kind, payload=body)
        if kind not in TRANSIENT_KINDS:
            self._history.append(published)
        for queue in self._subscribers:
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(published)
        for listener in self._listeners:
            listener(published)
        return published

    def replay_after(self, last_event_id: int) -> list[Event]:
        return [item for item in self._history if item.id > last_event_id]

    async def subscribe(self, last_event_id: int | None = None) -> AsyncIterator[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=EVENT_SUBSCRIBER_QUEUE_SIZE)
        self._subscribers.add(queue)
        try:
            delivered = last_event_id or 0
            if last_event_id is not None:
                for missed in self.replay_after(last_event_id):
                    delivered = missed.id
                    yield missed
            while True:
                item = await queue.get()
                if item.id > delivered:
                    delivered = item.id
                    yield item
        finally:
            self._subscribers.discard(queue)
