import asyncio
from collections.abc import Awaitable, Callable, Sequence

WORLD_GROUP = "world"


class EpochStoppedError(Exception):
    def __init__(self, phase: int) -> None:
        super().__init__(f"The epoch was stopped after phase {phase}.")
        self.phase = phase


class StopSignal:
    def __init__(self) -> None:
        self._requested = False

    @property
    def requested(self) -> bool:
        return self._requested

    def request(self) -> None:
        self._requested = True

    def clear(self) -> None:
        self._requested = False

    def checkpoint(self, phase: int) -> None:
        if self._requested:
            raise EpochStoppedError(phase)


async def pool[T](items: Sequence[T], workers: int, work: Callable[[T], Awaitable[None]], stop: StopSignal | None = None) -> None:
    queue = list(items)

    async def worker() -> None:
        while queue:
            if stop is not None and stop.requested:
                return
            await work(queue.pop(0))

    await asyncio.gather(*(worker() for _ in range(max(1, min(workers, len(queue))))))
