import asyncio
import logging
from dataclasses import dataclass
from io import BytesIO

from PIL import Image

from aerona.constants.media import THUMBNAIL_CONTENT_TYPE, THUMBNAIL_FORMAT, THUMBNAIL_QUALITY, THUMBNAIL_WIDTHS, UNRESIZED_EXTENSIONS
from aerona.core.account_scope import detached
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.media.errors import MediaStoreError
from aerona.media.keys import extension_of, thumbnail_key
from aerona.media.store import MediaStore, read_all

logger = logging.getLogger(__name__)

MISSING_FILE = "No such image file."
UNSUPPORTED_WIDTH = "Unsupported thumbnail width."


@dataclass(frozen=True)
class StoredImage:
    object_key: str
    content_type: str
    sha256: str
    width: int | None


@dataclass(frozen=True)
class MediaVariant:
    key: str
    content_type: str
    etag: str


def entity_tag(sha256: str, width: int | None = None) -> str:
    return f'"{sha256}"' if width is None else f'"{sha256}-w{width}"'


def render_thumbnail(data: bytes, width: int) -> bytes | None:
    with Image.open(BytesIO(data)) as image:
        if image.width <= width:
            return None
        height = max(1, round(image.height * width / image.width))
        resized = image.resize((width, height))
        if resized.mode not in ("RGB", "RGBA"):
            resized = resized.convert("RGBA")
        output = BytesIO()
        resized.save(output, format=THUMBNAIL_FORMAT, quality=THUMBNAIL_QUALITY)
        return output.getvalue()


class Thumbnailer:
    def __init__(self, store: MediaStore, concurrency: int, timeout_seconds: float) -> None:
        self._store = store
        self._semaphore = asyncio.Semaphore(max(1, concurrency))
        self._timeout = timeout_seconds
        self._pending: dict[str, asyncio.Task[bool]] = {}

    @property
    def store(self) -> MediaStore:
        return self._store

    async def variant(self, image: StoredImage, width: int | None) -> MediaVariant:
        original = MediaVariant(image.object_key, image.content_type, entity_tag(image.sha256))
        if width is None:
            return original
        if width not in THUMBNAIL_WIDTHS:
            raise ValidationFailedError(UNSUPPORTED_WIDTH)
        if extension_of(image.object_key) in UNRESIZED_EXTENSIONS or (image.width is not None and image.width <= width):
            return original
        key = thumbnail_key(image.object_key, width)
        thumbnail = MediaVariant(key, THUMBNAIL_CONTENT_TYPE, entity_tag(image.sha256, width))
        if await self._store.exists(key):
            return thumbnail
        task = self._pending.get(key)
        if task is None:
            task = detached(self._render(image.object_key, key, width))
            self._pending[key] = task
            task.add_done_callback(lambda _done: self._pending.pop(key, None))
        try:
            rendered = await asyncio.shield(task)
        except (TimeoutError, OSError, ValueError, MediaStoreError):
            logger.warning("thumbnail %s could not be rendered; serving the original", key)
            return original
        return thumbnail if rendered else original

    async def _render(self, source: str, target: str, width: int) -> bool:
        async with self._semaphore:
            data = await read_all(self._store, source)
            if data is None:
                raise NotFoundError(MISSING_FILE)
            rendered = await asyncio.wait_for(asyncio.to_thread(render_thumbnail, data, width), self._timeout)
            if rendered is None:
                return False
            await self._store.put(target, rendered)
            return True
