from aerona.constants.media import HTTP_SCHEME, HTTPS_SCHEME, MediaBackend
from aerona.media.file_store import FileMediaStore
from aerona.media.prefixed import PrefixedMediaStore
from aerona.media.s3_store import S3Config, S3MediaStore
from aerona.media.store import MediaStore
from aerona.settings import Settings

SCHEME_SEPARATOR = "://"


def endpoint_url(endpoint: str, secure: bool) -> str | None:
    cleaned = endpoint.strip().rstrip("/")
    if not cleaned:
        return None
    if SCHEME_SEPARATOR in cleaned:
        return cleaned
    return f"{HTTPS_SCHEME if secure else HTTP_SCHEME}{SCHEME_SEPARATOR}{cleaned}"


def s3_config(settings: Settings) -> S3Config:
    secret = settings.media_secret_key.get_secret_value()
    return S3Config(
        bucket=settings.media_bucket,
        endpoint_url=endpoint_url(settings.media_endpoint, settings.media_secure),
        access_key=settings.media_access_key or None,
        secret_key=secret or None,
        region=settings.media_region,
        secure=settings.media_secure,
    )


def create_media_store(settings: Settings) -> MediaStore:
    if settings.media_backend is not MediaBackend.S3:
        return FileMediaStore(settings.media_dir)
    shared = S3MediaStore(s3_config(settings))
    return PrefixedMediaStore(shared, settings.media_prefix) if settings.media_prefix else shared
