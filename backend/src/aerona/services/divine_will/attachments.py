import asyncio
import io
import mimetypes
import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath

from markitdown import MarkItDown, StreamInfo
from PIL import Image, UnidentifiedImageError

from aerona.core.grammar import several
from aerona.db.session import Database
from aerona.db.tables.divine_will import DivineWillAttachmentRow
from aerona.domain.enums.divine_will import AttachmentKind, AttachmentStatus
from aerona.media.store import MediaStore

MEDIA_PREFIX = "divine-will"
ORIGINAL_STEM = "original"
MARKDOWN_NAME = "document.md"
FALLBACK_MIME = "application/octet-stream"
FALLBACK_NAME = "attachment"
NAME_MAX_LENGTH = 200
SUFFIX_MAX_LENGTH = 12
MEGABYTE = 1024 * 1024
VISIBLE_IMAGES = frozenset({"image/png", "image/jpeg", "image/gif", "image/webp"})
SUFFIX = re.compile(r"^\.[A-Za-z0-9]{1,11}$")
UNSAFE_NAME = re.compile(r"[\x00-\x1f\\/]+")
TOO_MANY = "At most {limit} can go with one request; this one holds {sent}."
TOO_LARGE = "{name} is {size} MB; each file may be at most {limit} MB."
NO_FILES = "Attach at least one file."
NO_TEXT = "The file holds no text that could be read."
NOT_AN_IMAGE = "The file is not a picture that can be opened: {reason}"
NOT_CONVERTED = "The file could not be turned into text: {reason}"


class AttachmentRefusedError(Exception):
    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass(frozen=True)
class Upload:
    filename: str
    mime: str
    data: bytes


@dataclass(frozen=True)
class Stored:
    status: AttachmentStatus
    markdown: str
    note: str


def megabytes(size: int) -> str:
    return f"{size / MEGABYTE:.1f}".rstrip("0").rstrip(".")


def check_uploads(uploads: Sequence[Upload], max_files: int, max_mb: int) -> None:
    if not uploads:
        raise AttachmentRefusedError(NO_FILES, 422)
    if len(uploads) > max_files:
        raise AttachmentRefusedError(TOO_MANY.format(limit=several(max_files, "file", "files"), sent=several(len(uploads), "file", "files")), 422)
    for upload in uploads:
        if len(upload.data) > max_mb * MEGABYTE:
            raise AttachmentRefusedError(TOO_LARGE.format(name=upload.filename, size=megabytes(len(upload.data)), limit=max_mb), 413)


def clean_name(filename: str) -> str:
    name = UNSAFE_NAME.sub(" ", PurePosixPath(filename.replace("\\", "/")).name).strip()
    return name[:NAME_MAX_LENGTH] or FALLBACK_NAME


def suffix_of(filename: str) -> str:
    suffix = PurePosixPath(filename).suffix.lower()
    return suffix if SUFFIX.fullmatch(suffix) and len(suffix) <= SUFFIX_MAX_LENGTH else ""


def mime_of(filename: str, declared: str) -> str:
    stated = declared.split(";", 1)[0].strip().lower()
    if stated and stated != FALLBACK_MIME:
        return stated
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or stated or FALLBACK_MIME


def kind_of(mime: str) -> AttachmentKind:
    return AttachmentKind.IMAGE if mime in VISIBLE_IMAGES else AttachmentKind.DOCUMENT


def converted(data: bytes, filename: str, mime: str) -> str:
    info = StreamInfo(mimetype=mime, extension=suffix_of(filename) or None, filename=filename)
    result = MarkItDown(enable_plugins=False).convert_stream(io.BytesIO(data), stream_info=info)
    return result.markdown


def opened_image(data: bytes) -> None:
    with Image.open(io.BytesIO(data)) as picture:
        picture.verify()


def read_document(data: bytes, filename: str, mime: str) -> Stored:
    try:
        markdown = converted(data, filename, mime).strip()
    except Exception as error:
        return Stored(AttachmentStatus.UNREADABLE, "", NOT_CONVERTED.format(reason=str(error) or type(error).__name__))
    if not markdown:
        return Stored(AttachmentStatus.UNREADABLE, "", NO_TEXT)
    return Stored(AttachmentStatus.CONVERTED, markdown, "")


def read_image(data: bytes) -> Stored:
    try:
        opened_image(data)
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
        return Stored(AttachmentStatus.UNREADABLE, "", NOT_AN_IMAGE.format(reason=str(error) or type(error).__name__))
    return Stored(AttachmentStatus.STORED, "", "")


async def store_uploads(database: Database, media: MediaStore, uploads: Sequence[Upload]) -> list[DivineWillAttachmentRow]:
    rows: list[DivineWillAttachmentRow] = []
    for upload in uploads:
        name = clean_name(upload.filename)
        mime = mime_of(name, upload.mime)
        kind = kind_of(mime)
        folder = f"{MEDIA_PREFIX}/{uuid.uuid4().hex}"
        original = f"{folder}/{ORIGINAL_STEM}{suffix_of(name)}"
        await media.put(original, upload.data)
        if kind is AttachmentKind.IMAGE:
            stored = await asyncio.to_thread(read_image, upload.data)
        else:
            stored = await asyncio.to_thread(read_document, upload.data, name, mime)
        markdown_key = ""
        if stored.markdown:
            markdown_key = f"{folder}/{MARKDOWN_NAME}"
            await media.put(markdown_key, stored.markdown.encode("utf-8"))
        rows.append(
            DivineWillAttachmentRow(
                cycle_id=None,
                kind=kind,
                filename=name,
                mime=mime,
                size=len(upload.data),
                media_key=original,
                markdown_key=markdown_key,
                status=stored.status,
                seen_by_model=False,
                note=stored.note,
            )
        )
    async with database.write() as session:
        session.add_all(rows)
        await session.flush()
    return rows
