import asyncio
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import AsyncExitStack
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from aiobotocore.config import AioConfig
from aiobotocore.response import StreamingBody
from aiobotocore.session import get_session
from botocore.exceptions import BotoCoreError, ClientError
from types_aiobotocore_s3.client import S3Client
from types_aiobotocore_s3.literals import BucketLocationConstraintType

from aerona.constants.media import (
    MEDIA_CHUNK_BYTES,
    S3_ADDRESSING_STYLE,
    S3_CONNECT_TIMEOUT_SECONDS,
    S3_DEFAULT_REGION,
    S3_MAX_ATTEMPTS,
    S3_MISSING_CODES,
    S3_READ_TIMEOUT_SECONDS,
    S3_RETRY_MODE,
    S3_SERVICE_NAME,
    S3_SIGNATURE_VERSION,
)
from aerona.media.errors import InvalidMediaKeyError, MediaStoreError
from aerona.media.keys import content_type_of, is_valid_prefix, require_valid_key
from aerona.media.store import MediaObject, ObjectInfo

UNAVAILABLE = "The media store is not reachable."


@dataclass(frozen=True)
class S3Config:
    bucket: str
    endpoint_url: str | None
    access_key: str | None
    secret_key: str | None
    region: str
    secure: bool


def is_missing(error: ClientError) -> bool:
    return str(error.response.get("Error", {}).get("Code", "")) in S3_MISSING_CODES


class S3MediaStore:
    def __init__(self, config: S3Config, chunk_bytes: int = MEDIA_CHUNK_BYTES) -> None:
        self._config = config
        self._chunk = chunk_bytes
        self._stack = AsyncExitStack()
        self._client: S3Client | None = None
        self._lock = asyncio.Lock()

    @property
    def bucket(self) -> str:
        return self._config.bucket

    async def _s3(self) -> S3Client:
        if self._client is not None:
            return self._client
        async with self._lock:
            if self._client is None:
                config = AioConfig(
                    signature_version=S3_SIGNATURE_VERSION,
                    s3={"addressing_style": S3_ADDRESSING_STYLE},
                    retries={"max_attempts": S3_MAX_ATTEMPTS, "mode": S3_RETRY_MODE},
                    connect_timeout=S3_CONNECT_TIMEOUT_SECONDS,
                    read_timeout=S3_READ_TIMEOUT_SECONDS,
                )
                creator = get_session().create_client(
                    S3_SERVICE_NAME,
                    endpoint_url=self._config.endpoint_url,
                    region_name=self._config.region,
                    aws_access_key_id=self._config.access_key,
                    aws_secret_access_key=self._config.secret_key,
                    use_ssl=self._config.secure,
                    config=config,
                )
                self._client = await self._stack.enter_async_context(creator)
            client: S3Client = self._client
            return client

    async def ensure_ready(self) -> None:
        client = await self._s3()
        try:
            await client.head_bucket(Bucket=self.bucket)
            return
        except ClientError as error:
            if not is_missing(error):
                raise MediaStoreError(UNAVAILABLE) from error
        except BotoCoreError as error:
            raise MediaStoreError(UNAVAILABLE) from error
        try:
            if self._config.region == S3_DEFAULT_REGION:
                await client.create_bucket(Bucket=self.bucket)
            else:
                await client.create_bucket(
                    Bucket=self.bucket, CreateBucketConfiguration={"LocationConstraint": cast("BucketLocationConstraintType", self._config.region)}
                )
        except (ClientError, BotoCoreError) as error:
            raise MediaStoreError(UNAVAILABLE) from error

    async def put(self, key: str, data: bytes) -> ObjectInfo:
        client = await self._s3()
        content_type = content_type_of(require_valid_key(key))
        try:
            await client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type, ContentLength=len(data))
        except (ClientError, BotoCoreError) as error:
            raise MediaStoreError(UNAVAILABLE) from error
        return ObjectInfo(key=key, size=len(data), content_type=content_type, last_modified=datetime.now(UTC))

    async def head(self, key: str) -> ObjectInfo | None:
        client = await self._s3()
        require_valid_key(key)
        try:
            response = await client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as error:
            if is_missing(error):
                return None
            raise MediaStoreError(UNAVAILABLE) from error
        except BotoCoreError as error:
            raise MediaStoreError(UNAVAILABLE) from error
        return ObjectInfo(
            key=key,
            size=int(response.get("ContentLength", 0)),
            content_type=response.get("ContentType") or content_type_of(key),
            last_modified=response.get("LastModified") or datetime.now(UTC),
        )

    async def exists(self, key: str) -> bool:
        return await self.head(key) is not None

    async def get(self, key: str) -> MediaObject | None:
        client = await self._s3()
        require_valid_key(key)
        try:
            response = await client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as error:
            if is_missing(error):
                return None
            raise MediaStoreError(UNAVAILABLE) from error
        except BotoCoreError as error:
            raise MediaStoreError(UNAVAILABLE) from error
        info = ObjectInfo(
            key=key,
            size=int(response.get("ContentLength", 0)),
            content_type=response.get("ContentType") or content_type_of(key),
            last_modified=response.get("LastModified") or datetime.now(UTC),
        )
        return MediaObject(info=info, chunks=self._chunks(response["Body"]))

    async def _chunks(self, body: StreamingBody) -> AsyncGenerator[bytes]:
        try:
            async for chunk in body.iter_chunks(self._chunk):
                yield chunk
        finally:
            body.close()

    async def delete(self, key: str) -> None:
        client = await self._s3()
        require_valid_key(key)
        try:
            await client.delete_object(Bucket=self.bucket, Key=key)
        except ClientError as error:
            if not is_missing(error):
                raise MediaStoreError(UNAVAILABLE) from error
        except BotoCoreError as error:
            raise MediaStoreError(UNAVAILABLE) from error

    async def list(self, prefix: str) -> AsyncIterator[ObjectInfo]:
        if not is_valid_prefix(prefix):
            raise InvalidMediaKeyError("Invalid media prefix.")
        client = await self._s3()
        paginator = client.get_paginator("list_objects_v2")
        try:
            async for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                for item in page.get("Contents", []):
                    key = item.get("Key", "")
                    modified = item.get("LastModified") or datetime.now(UTC)
                    yield ObjectInfo(key=key, size=int(item.get("Size", 0)), content_type=content_type_of(key), last_modified=modified)
        except ClientError as error:
            if is_missing(error):
                return
            raise MediaStoreError(UNAVAILABLE) from error
        except BotoCoreError as error:
            raise MediaStoreError(UNAVAILABLE) from error

    async def close(self) -> None:
        await self._stack.aclose()
        self._client = None
