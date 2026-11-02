from collections.abc import AsyncGenerator, AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ObjectInfo:
    key: str
    size: int
    content_type: str
    last_modified: datetime


@dataclass(frozen=True)
class MediaObject:
    info: ObjectInfo
    chunks: AsyncGenerator[bytes]

    async def aclose(self) -> None:
        await self.chunks.aclose()


@runtime_checkable
class MediaStore(Protocol):
    async def ensure_ready(self) -> None: ...

    async def put(self, key: str, data: bytes) -> ObjectInfo: ...

    async def get(self, key: str) -> MediaObject | None: ...

    async def head(self, key: str) -> ObjectInfo | None: ...

    async def exists(self, key: str) -> bool: ...

    async def delete(self, key: str) -> None: ...

    def list(self, prefix: str) -> AsyncIterator[ObjectInfo]: ...

    async def close(self) -> None: ...


async def read_all(store: MediaStore, key: str) -> bytes | None:
    opened = await store.get(key)
    if opened is None:
        return None
    parts: list[bytes] = []
    try:
        async for chunk in opened.chunks:
            parts.append(chunk)
    finally:
        await opened.aclose()
    return b"".join(parts)


async def list_keys(store: MediaStore, prefix: str) -> list[ObjectInfo]:
    return [info async for info in store.list(prefix)]
