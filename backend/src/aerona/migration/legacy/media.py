from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

from aerona.constants.media import MediaBackend
from aerona.media.factory import create_media_store
from aerona.media.file_store import FileMediaStore
from aerona.media.keys import content_type_of
from aerona.media.store import MediaObject, MediaStore, ObjectInfo
from aerona.settings import Settings


class DryRunMediaStore:
    def __init__(self) -> None:
        self.keys: dict[str, int] = {}

    async def ensure_ready(self) -> None:
        return None

    async def put(self, key: str, data: bytes) -> ObjectInfo:
        self.keys[key] = len(data)
        return ObjectInfo(key=key, size=len(data), content_type=content_type_of(key), last_modified=datetime.now(UTC))

    async def get(self, key: str) -> MediaObject | None:
        return None

    async def head(self, key: str) -> ObjectInfo | None:
        size = self.keys.get(key)
        if size is None:
            return None
        return ObjectInfo(key=key, size=size, content_type=content_type_of(key), last_modified=datetime.now(UTC))

    async def exists(self, key: str) -> bool:
        return key in self.keys

    async def delete(self, key: str) -> None:
        self.keys.pop(key, None)

    async def list(self, prefix: str) -> AsyncIterator[ObjectInfo]:
        for key, size in sorted(self.keys.items()):
            if key.startswith(prefix):
                yield ObjectInfo(key=key, size=size, content_type=content_type_of(key), last_modified=datetime.now(UTC))

    async def close(self) -> None:
        return None


def open_media_store(backend: MediaBackend, media_dir: Path | None, settings: Settings, dry_run: bool) -> MediaStore:
    if dry_run:
        return DryRunMediaStore()
    if backend is MediaBackend.FILE:
        return FileMediaStore(media_dir) if media_dir is not None else create_media_store(settings.model_copy(update={"media_backend": MediaBackend.FILE}))
    return create_media_store(settings.model_copy(update={"media_backend": MediaBackend.S3}))
