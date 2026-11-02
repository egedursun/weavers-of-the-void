import asyncio
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta

from aerona.constants.media import MEDIA_COLLECT_GRACE_SECONDS, ORIGINALS_PREFIX, THUMBNAILS_PREFIX
from aerona.media.keys import is_original_key, stem_of, thumbnail_keys, thumbnail_stem
from aerona.media.store import MediaStore, list_keys

ReferenceSource = Callable[[], set[str] | None]


class MediaCollector:
    def __init__(self, store: MediaStore, references: ReferenceSource, grace_seconds: float = MEDIA_COLLECT_GRACE_SECONDS) -> None:
        self._store = store
        self._references = references
        self._grace = timedelta(seconds=grace_seconds)

    @property
    def store(self) -> MediaStore:
        return self._store

    async def used(self) -> set[str] | None:
        return await asyncio.to_thread(self._references)

    async def collect(self, keys: Iterable[str]) -> int:
        candidates = {key for key in keys if is_original_key(key)}
        if not candidates:
            return 0
        used = await self.used()
        if used is None:
            return 0
        removed = 0
        for key in sorted(candidates - used):
            await self.remove(key)
            removed += 1
        return removed

    async def remove(self, key: str) -> None:
        await self._store.delete(key)
        for thumbnail in thumbnail_keys(key):
            await self._store.delete(thumbnail)

    async def sweep(self) -> int:
        used = await self.used()
        if used is None:
            return 0
        cutoff = datetime.now(UTC) - self._grace
        removed = 0
        for info in await list_keys(self._store, ORIGINALS_PREFIX):
            if info.key not in used and info.last_modified <= cutoff:
                await self.remove(info.key)
                removed += 1
        stems = {stem_of(key) for key in used}
        for info in await list_keys(self._store, THUMBNAILS_PREFIX):
            stem = thumbnail_stem(info.key)
            if stem is not None and stem not in stems and info.last_modified <= cutoff:
                await self._store.delete(info.key)
        return removed
