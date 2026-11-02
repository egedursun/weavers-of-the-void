import re
from pathlib import PurePosixPath

from aerona.constants.media import (
    CONTENT_TYPES,
    DEFAULT_CONTENT_TYPE,
    KEY_SEPARATOR,
    MEDIA_KEY_MAX_LENGTH,
    MEDIA_KEY_SEGMENT_PATTERN,
    ORIGINALS_PREFIX,
    SHA256_HEX_PATTERN,
    THUMBNAIL_EXTENSION,
    THUMBNAIL_WIDTHS,
    THUMBNAILS_PREFIX,
)
from aerona.media.errors import InvalidMediaKeyError

SEGMENT = re.compile(MEDIA_KEY_SEGMENT_PATTERN)
SHA256_HEX = re.compile(SHA256_HEX_PATTERN)
PARENT_SEGMENT = ".."
ORIGINAL_DEPTH = 2
THUMBNAIL_DEPTH = 3


def is_valid_key(key: str) -> bool:
    if not key or len(key) > MEDIA_KEY_MAX_LENGTH:
        return False
    segments = key.split(KEY_SEPARATOR)
    return all(SEGMENT.match(segment) and PARENT_SEGMENT not in segment for segment in segments)


def require_valid_key(key: str) -> str:
    if not is_valid_key(key):
        raise InvalidMediaKeyError("Invalid media key.")
    return key


def is_valid_prefix(prefix: str) -> bool:
    if not prefix:
        return True
    head = prefix.rstrip(KEY_SEPARATOR)
    return not head or is_valid_key(head)


def is_original_key(key: str) -> bool:
    segments = key.split(KEY_SEPARATOR)
    return is_valid_key(key) and key.startswith(ORIGINALS_PREFIX) and len(segments) == ORIGINAL_DEPTH and PurePosixPath(key).suffix.lower() in CONTENT_TYPES


def is_sha256(value: str | None) -> bool:
    return value is not None and bool(SHA256_HEX.match(value))


def original_key(file_name: str) -> str:
    return require_valid_key(f"{ORIGINALS_PREFIX}{file_name}")


def stem_of(key: str) -> str:
    return PurePosixPath(key).stem


def extension_of(key: str) -> str:
    return PurePosixPath(key).suffix.lower()


def thumbnail_key(original: str, width: int) -> str:
    return require_valid_key(f"{THUMBNAILS_PREFIX}{width}{KEY_SEPARATOR}{stem_of(original)}{THUMBNAIL_EXTENSION}")


def thumbnail_keys(original: str) -> list[str]:
    return [thumbnail_key(original, width) for width in sorted(THUMBNAIL_WIDTHS)]


def thumbnail_stem(key: str) -> str | None:
    segments = key.split(KEY_SEPARATOR)
    if not key.startswith(THUMBNAILS_PREFIX) or len(segments) != THUMBNAIL_DEPTH:
        return None
    return stem_of(key)


def content_type_of(key: str) -> str:
    return CONTENT_TYPES.get(extension_of(key), DEFAULT_CONTENT_TYPE)
