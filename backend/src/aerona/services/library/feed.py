import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime

from aerona.constants.limits import EVENT_SUBSCRIBER_QUEUE_SIZE
from aerona.domain.enums.library_jobs import LibraryStreamKind


@dataclass(frozen=True)
class LibraryNotice:
    id: int
    kind: LibraryStreamKind
    universe_id: str | None = None
    job_id: str | None = None
    at: datetime = field(default_factory=lambda: datetime.now(UTC))


class LibraryFeed:
    def __init__(self) -> None:
        self._sequence = 0
        self._subscribers: set[asyncio.Queue[LibraryNotice]] = set()

    @property
    def last_id(self) -> int:
        return self._sequence

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    def publish(self, kind: LibraryStreamKind, *, universe_id: str | None = None, job_id: str | None = None) -> LibraryNotice:
        self._sequence += 1
        notice = LibraryNotice(id=self._sequence, kind=kind, universe_id=universe_id, job_id=job_id)
        for queue in self._subscribers:
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(notice)
        return notice

    async def subscribe(self) -> AsyncIterator[LibraryNotice]:
        queue: asyncio.Queue[LibraryNotice] = asyncio.Queue(maxsize=EVENT_SUBSCRIBER_QUEUE_SIZE)
        self._subscribers.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.discard(queue)
