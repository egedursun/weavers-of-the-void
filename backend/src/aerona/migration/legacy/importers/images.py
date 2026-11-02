import asyncio
import hashlib
import re
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path, PurePosixPath

from PIL import Image

from aerona.constants.media import MEDIA_KEY_SEGMENT_PATTERN
from aerona.constants.schema import IMAGE_FILE_NAME_MAX_LENGTH
from aerona.db.tables.meta import ImageRow
from aerona.domain.enums.meta import ImageMime, ImageOrigin
from aerona.media.keys import original_key
from aerona.media.store import MediaStore
from aerona.migration.legacy.context import MigrationContext
from aerona.migration.legacy.timestamps import legacy_time
from aerona.services.images.records import CAPTION_MAX_LENGTH, EXTENSIONS, MAGIC, caption_valid, detect_mime

SAFE_NAME = re.compile(MEDIA_KEY_SEGMENT_PATTERN)
NAME_SEPARATOR = "-"


@dataclass
class UploadLog:
    written: list[str] = field(default_factory=list)


def detected_mime(data: bytes) -> ImageMime | None:
    return next((mime for mime in MAGIC if detect_mime(data, mime)), None)


def dimensions(data: bytes) -> tuple[int | None, int | None]:
    try:
        with Image.open(BytesIO(data)) as image:
            return image.width, image.height
    except (OSError, ValueError):
        return None, None


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ImageImporter:
    def __init__(self, context: MigrationContext, store: MediaStore, legacy_dir: Path, log: UploadLog) -> None:
        self.context = context
        self.store = store
        self.directory = legacy_dir / context.vocabulary.image_directory
        self.log = log
        self.keys_by_digest: dict[str, str] = {}
        self.file_names: set[str] = set()

    def _file_name(self, legacy_id: int, raw: str, mime: ImageMime) -> str | None:
        name = PurePosixPath(raw).name
        if not SAFE_NAME.match(name) or ".." in name:
            return None
        path = PurePosixPath(name)
        if path.suffix.lower() not in EXTENSIONS.values():
            name = f"{path.stem}{EXTENSIONS[mime]}"
        if name in self.file_names:
            stem, suffix = PurePosixPath(name).stem, PurePosixPath(name).suffix
            name = f"{stem}{NAME_SEPARATOR}{legacy_id}{suffix}"
        name = name[:IMAGE_FILE_NAME_MAX_LENGTH]
        self.file_names.add(name)
        return name

    async def _object_key(self, data: bytes, sha: str, file_name: str) -> str:
        images = self.context.report.images
        shared = self.keys_by_digest.get(sha)
        if shared is not None:
            images.deduplicated += 1
            return shared
        key = original_key(file_name)
        if await self.store.exists(key):
            images.already_stored += 1
        else:
            await self.store.put(key, data)
            self.log.written.append(key)
            images.uploaded += 1
            images.bytes_uploaded += len(data)
        self.keys_by_digest[sha] = key
        return key

    async def run(self) -> None:
        report = self.context.report
        images = report.images
        thumbnails = self.directory / self.context.vocabulary.thumbnail_directory
        if thumbnails.is_dir():
            images.skipped_thumbnails = sum(1 for path in thumbnails.rglob("*") if path.is_file())
        referenced: set[str] = set()
        for row in self.context.source.iterate("images", ("id",)):
            images.rows += 1
            legacy_id = row.integer("id") or 0
            reference = f"image:{legacy_id}"
            target = self.context.node(row.text("target_kind"), row.integer("target_id"))
            raw_name = row.text("file_name")
            if target is None or raw_name is None:
                images.unlinked += 1
                report.place_failed("image", reference, "the image target is missing")
                continue
            path = self.directory / PurePosixPath(raw_name).name
            referenced.add(path.name)
            if not path.is_file():
                images.missing_files += 1
                report.place_failed("image", reference, f"file {raw_name} is missing")
                continue
            data = await asyncio.to_thread(path.read_bytes)
            mime = detected_mime(data)
            if mime is None:
                report.place_failed("image", reference, f"file {raw_name} is not a png, jpeg or webp image")
                continue
            file_name = self._file_name(legacy_id, raw_name, mime)
            if file_name is None:
                report.place_failed("image", reference, f"file name {raw_name!r} is not safe")
                continue
            sha = digest(data)
            key = await self._object_key(data, sha, file_name)
            width, height = await asyncio.to_thread(dimensions, data)
            caption = row.text("caption")
            image = ImageRow(
                target_node_id=target,
                file_name=file_name,
                object_key=key,
                sha256=sha,
                mime=mime,
                origin=ImageOrigin.GENERATED,
                caption=caption.strip()[:CAPTION_MAX_LENGTH] if caption is not None and caption_valid(caption) else None,
                is_cover=row.flag("cover"),
                size_bytes=len(data),
                width=width,
                height=height,
            )
            stamp = legacy_time(row.raw("created_at"))
            if stamp is not None:
                image.created_at = stamp
            self.context.add(image)
            images.linked += 1
            await self.context.flush_if_full()
        await self.context.flush()
        if self.directory.is_dir():
            images.files_without_rows = sum(
                1 for path in self.directory.iterdir() if path.is_file() and not path.name.startswith(".") and path.name not in referenced
            )


async def import_images(context: MigrationContext, store: MediaStore, legacy_dir: Path, log: UploadLog) -> None:
    await ImageImporter(context, store, legacy_dir, log).run()


async def remove_uploads(store: MediaStore, log: UploadLog) -> int:
    removed = 0
    for key in reversed(log.written):
        await store.delete(key)
        removed += 1
    log.written.clear()
    return removed
