import asyncio
import heapq
import itertools

from aerona_image_worker.domain.enums import PRIORITY_RANK
from aerona_image_worker.jobs.job import Job


class JobQueue:
    def __init__(self) -> None:
        self._heap: list[tuple[int, int, Job]] = []
        self._counter = itertools.count()
        self._available = asyncio.Event()

    def __len__(self) -> int:
        return len(self._heap)

    def push(self, job: Job) -> None:
        heapq.heappush(self._heap, (PRIORITY_RANK[job.priority], next(self._counter), job))
        self._available.set()

    def remove(self, job: Job) -> bool:
        remaining = [entry for entry in self._heap if entry[2] is not job]
        if len(remaining) == len(self._heap):
            return False
        heapq.heapify(remaining)
        self._heap = remaining
        if not self._heap:
            self._available.clear()
        return True

    def position(self, job: Job) -> int | None:
        ordered = [entry[2] for entry in sorted(self._heap, key=lambda entry: entry[:2])]
        return ordered.index(job) if job in ordered else None

    async def pop(self) -> Job:
        while not self._heap:
            self._available.clear()
            await self._available.wait()
        job = heapq.heappop(self._heap)[2]
        if not self._heap:
            self._available.clear()
        return job
