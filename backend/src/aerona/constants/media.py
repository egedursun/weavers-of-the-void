from enum import StrEnum
from typing import Final


class MediaBackend(StrEnum):
    FILE = "file"
    S3 = "s3"


DEFAULT_MEDIA_BUCKET = "aerona-media"
DEFAULT_MEDIA_REGION = "us-east-1"
DEFAULT_MEDIA_ENDPOINT = ""
ORIGINALS_PREFIX = "originals/"
THUMBNAILS_PREFIX = "thumbnails/"
KEY_SEPARATOR = "/"
MEDIA_KEY_MAX_LENGTH = 512
MEDIA_KEY_SEGMENT_PATTERN = r"^[\w-][\w.-]*$"
THUMBNAIL_WIDTHS = frozenset({64, 160, 320, 640, 960, 1280})
THUMBNAIL_EXTENSION = ".webp"
THUMBNAIL_FORMAT = "WEBP"
THUMBNAIL_CONTENT_TYPE = "image/webp"
THUMBNAIL_QUALITY = 85
UNRESIZED_EXTENSIONS = frozenset({".gif", ".svg"})
CONTENT_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".avif": "image/avif",
}
DEFAULT_CONTENT_TYPE = "application/octet-stream"
MEDIA_CHUNK_BYTES = 256 * 1024
MEDIA_COLLECT_GRACE_SECONDS = 3600.0
PARTIAL_SUFFIX = ".partial"
PARTIAL_TOKEN_BYTES = 6
SHA256_HEX_LENGTH = 64
SHA256_HEX_PATTERN = r"^[0-9a-f]{64}$"
S3_SERVICE_NAME: Final = "s3"
S3_ADDRESSING_STYLE = "path"
S3_SIGNATURE_VERSION = "s3v4"
S3_RETRY_MODE = "standard"
S3_MAX_ATTEMPTS = 3
S3_CONNECT_TIMEOUT_SECONDS = 5.0
S3_READ_TIMEOUT_SECONDS = 60.0
S3_MISSING_CODES = frozenset({"404", "NoSuchKey", "NotFound", "NoSuchBucket"})
S3_DEFAULT_REGION = "us-east-1"
HTTP_SCHEME = "http"
HTTPS_SCHEME = "https"
