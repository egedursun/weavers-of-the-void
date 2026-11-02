import asyncio
import os
import secrets
from collections.abc import AsyncGenerator, AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

from aerona.constants.media import KEY_SEPARATOR, MEDIA_CHUNK_BYTES, PARTIAL_SUFFIX, PARTIAL_TOKEN_BYTES
from aerona.media.errors import InvalidMediaKeyError
from aerona.media.keys import content_type_of, is_valid_key, is_valid_prefix, require_valid_key
from aerona.media.store import MediaObject, ObjectInfo


def describe(key: str, path: Path) -> ObjectInfo:
    stat = path.stat()
    return ObjectInfo(key=key, size=stat.st_size, content_type=content_type_of(key), last_modified=datetime.fromtimestamp(stat.st_mtime, UTC))


def stat_of(key: str, path: Path) -> ObjectInfo | None:
    try:
        return describe(key, path) if path.is_file() else None
    except FileNotFoundError:
        return None


def scan(root: Path, prefix: str) -> list[ObjectInfo]:
    directory = prefix.rpartition(KEY_SEPARATOR)[0]
    base = root.joinpath(*directory.split(KEY_SEPARATOR)) if directory else root
    if not base.is_dir():
        return []
    found: list[ObjectInfo] = []
    for path in sorted(base.rglob("*")):
        key = path.relative_to(root).as_posix()
        if path.name.endswith(PARTIAL_SUFFIX) or not key.startswith(prefix) or not is_valid_key(key):
            continue
        info = stat_of(key, path)
        if info is not None:
            found.append(info)
    return found


class FileMediaStore:
    def __init__(self, root: Path, chunk_bytes: int = MEDIA_CHUNK_BYTES) -> None:
        self._root = root
        self._chunk = chunk_bytes

    @property
    def root(self) -> Path:
        return self._root

    def _path(self, key: str) -> Path:
        return self._root.joinpath(*require_valid_key(key).split(KEY_SEPARATOR))

    async def ensure_ready(self) -> None:
        await asyncio.to_thread(self._root.mkdir, parents=True, exist_ok=True)

    async def put(self, key: str, data: bytes) -> ObjectInfo:
        path = self._path(key)
        return await asyncio.to_thread(self._write, key, path, data)

    def _write(self, key: str, path: Path, data: bytes) -> ObjectInfo:
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_name(f"{path.name}.{secrets.token_hex(PARTIAL_TOKEN_BYTES)}{PARTIAL_SUFFIX}")
        try:
            partial.write_bytes(data)
            os.replace(partial, path)
        finally:
            partial.unlink(missing_ok=True)
        return describe(key, path)

    async def head(self, key: str) -> ObjectInfo | None:
        return await asyncio.to_thread(stat_of, key, self._path(key))

    async def exists(self, key: str) -> bool:
        return await self.head(key) is not None

    async def get(self, key: str) -> MediaObject | None:
        path = self._path(key)
        try:
            handle = await asyncio.to_thread(path.open, "rb")
        except (FileNotFoundError, IsADirectoryError):
            return None
        info = await asyncio.to_thread(describe, key, path)
        return MediaObject(info=info, chunks=self._chunks(handle))

    async def _chunks(self, handle: BinaryIO) -> AsyncGenerator[bytes]:
        try:
            while chunk := await asyncio.to_thread(handle.read, self._chunk):
                yield chunk
        finally:
            await asyncio.to_thread(handle.close)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._path(key).unlink, True)

    async def list(self, prefix: str) -> AsyncIterator[ObjectInfo]:
        if not is_valid_prefix(prefix):
            raise InvalidMediaKeyError("Invalid media prefix.")
        for info in await asyncio.to_thread(scan, self._root, prefix):
            yield info

    async def close(self) -> None:
        return None
