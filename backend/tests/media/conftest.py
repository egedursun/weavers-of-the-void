import secrets
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from moto.server import ThreadedMotoServer

from aerona.media.file_store import FileMediaStore
from aerona.media.s3_store import S3Config, S3MediaStore
from aerona.media.store import MediaStore

LOOPBACK = "127.0.0.1"
FAKE_CREDENTIAL = "testing"
FAKE_REGION = "us-east-1"
BUCKET_TOKEN_BYTES = 4


@pytest.fixture(scope="session")
def s3_endpoint() -> Iterator[str]:
    server = ThreadedMotoServer(ip_address=LOOPBACK, port=0, verbose=False)
    server.start()
    host, port = server.get_host_and_port()
    try:
        yield f"http://{host}:{port}"
    finally:
        server.stop()


def s3_config(endpoint: str, bucket: str | None = None) -> S3Config:
    return S3Config(
        bucket=bucket or f"aerona-test-{secrets.token_hex(BUCKET_TOKEN_BYTES)}",
        endpoint_url=endpoint,
        access_key=FAKE_CREDENTIAL,
        secret_key=FAKE_CREDENTIAL,
        region=FAKE_REGION,
        secure=False,
    )


@pytest.fixture
async def s3_store(s3_endpoint: str) -> AsyncIterator[S3MediaStore]:
    store = S3MediaStore(s3_config(s3_endpoint), chunk_bytes=7)
    await store.ensure_ready()
    yield store
    await store.close()


@pytest.fixture
async def file_store(tmp_path: Path) -> AsyncIterator[FileMediaStore]:
    store = FileMediaStore(tmp_path / "media", chunk_bytes=7)
    await store.ensure_ready()
    yield store
    await store.close()


@pytest.fixture(params=["file", "s3"])
async def media_store(request: pytest.FixtureRequest, tmp_path: Path, s3_endpoint: str) -> AsyncIterator[MediaStore]:
    store: MediaStore = FileMediaStore(tmp_path / "media", chunk_bytes=7) if request.param == "file" else S3MediaStore(s3_config(s3_endpoint), chunk_bytes=7)
    await store.ensure_ready()
    yield store
    await store.close()
