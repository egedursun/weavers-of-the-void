from collections.abc import AsyncIterator
from dataclasses import replace

from aerona.constants.media import KEY_SEPARATOR
from aerona.media.errors import InvalidMediaKeyError
from aerona.media.keys import is_valid_prefix, require_valid_key
from aerona.media.store import MediaObject, MediaStore, ObjectInfo

INVALID_SCOPE = "Invalid media scope."


class PrefixedMediaStore:
    def __init__(self, inner: MediaStore, prefix: str) -> None:
        if not prefix.endswith(KEY_SEPARATOR) or not is_valid_prefix(prefix):
            raise InvalidMediaKeyError(INVALID_SCOPE)
        self._inner = inner
        self._prefix = prefix

    def scoped(self, key: str) -> str:
        return require_valid_key(f"{self._prefix}{require_valid_key(key)}")

    def local(self, info: ObjectInfo) -> ObjectInfo:
        return replace(info, key=info.key.removeprefix(self._prefix))

    async def ensure_ready(self) -> None:
        await self._inner.ensure_ready()

    async def put(self, key: str, data: bytes) -> ObjectInfo:
        return self.local(await self._inner.put(self.scoped(key), data))

    async def get(self, key: str) -> MediaObject | None:
        found = await self._inner.get(self.scoped(key))
        return MediaObject(info=self.local(found.info), chunks=found.chunks) if found is not None else None

    async def head(self, key: str) -> ObjectInfo | None:
        found = await self._inner.head(self.scoped(key))
        return self.local(found) if found is not None else None

    async def exists(self, key: str) -> bool:
        return await self._inner.exists(self.scoped(key))

    async def delete(self, key: str) -> None:
        await self._inner.delete(self.scoped(key))

    async def list(self, prefix: str) -> AsyncIterator[ObjectInfo]:
        if not is_valid_prefix(prefix):
            raise InvalidMediaKeyError("Invalid media prefix.")
        async for info in self._inner.list(f"{self._prefix}{prefix}"):
            if info.key.startswith(self._prefix):
                yield self.local(info)

    async def close(self) -> None:
        await self._inner.close()
