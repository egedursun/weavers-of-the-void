MEGABYTE = 1024 * 1024
JSON_BODY_MAX_BYTES = 2 * MEGABYTE
IMAGE_UPLOAD_MAX_BYTES = 30 * MEGABYTE
PACKAGE_UPLOAD_MAX_BYTES = 400 * MEGABYTE
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "[::1]", "::1"})
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
ALLOWED_FETCH_SITES = frozenset({"same-origin", "none"})
SIMPLE_CONTENT_TYPES = frozenset({"text/plain", "application/x-www-form-urlencoded", "multipart/form-data"})
JSON_CONTENT_TYPE = "application/json"
OCTET_STREAM = "application/octet-stream"
IMAGE_CONTENT_PREFIX = "image/"
NULL_ORIGIN = "null"
CORRELATION_ID_LENGTH = 12
SCRUBBED_PATH = "…"
LOCK_FILENAME = "aerona.lock"
MEDIA_PATH = "/media"
BOOK_PATH = "/book"
CODEX_FILENAME_SUFFIX = "-codex.md"
SQLITE_MEDIA_TYPE = "application/vnd.sqlite3"
PACKAGE_MEDIA_TYPE = "application/octet-stream"
MARKDOWN_MEDIA_TYPE = "text/markdown; charset=utf-8"
CSV_MEDIA_TYPE = "text/csv; charset=utf-8"
IMMUTABLE_CACHE = "public, max-age=31536000, immutable"
PUBLIC_FILE_CACHE = "public, max-age=86400"
NO_CACHE = "no-cache"
BOOK_CSP = (
    "default-src 'none'; img-src 'self' data:; font-src 'self'; style-src 'unsafe-inline'; script-src 'nonce-{nonce}'; "
    "connect-src 'self'; base-uri 'none'; form-action 'none'"
)
GRAPH_PAGE_DEFAULT = 2000
GRAPH_PAGE_MAX = 20000
ENTITY_PAGE_DEFAULT = 200
ENTITY_PAGE_MAX = 2000
CARD_PAGE_DEFAULT = 48
CARD_PAGE_MAX = 200
RELATION_PAGE_DEFAULT = 100
RELATION_PAGE_MAX = 1000
SEARCH_MIN_LENGTH = 2
PATH_MAX_DEPTH = 6
STATIC_INDEX = "index.html"
WIKI_TIMELINE_LINES = 40
SCOPED_PAGE = 40
SCOPED_PAGE_MAX = 500
WIKI_PEOPLES_SHOWN = 12
ERROR_DESCRIPTION = "The error and its code"
ERROR_SCHEMA_REF = "#/components/schemas/ErrorResponse"
