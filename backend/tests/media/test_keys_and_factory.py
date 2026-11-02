from pathlib import Path

import pytest
from pydantic import SecretStr

from aerona.constants.media import MediaBackend
from aerona.media.factory import create_media_store, endpoint_url, s3_config
from aerona.media.file_store import FileMediaStore
from aerona.media.keys import content_type_of, is_original_key, is_sha256, original_key, thumbnail_key, thumbnail_keys, thumbnail_stem
from aerona.media.s3_store import S3MediaStore
from aerona.settings import Settings


def test_object_key_layout() -> None:
    assert original_key("entity3-1-abc.png") == "originals/entity3-1-abc.png"
    assert thumbnail_key("originals/entity3-1-abc.png", 160) == "thumbnails/160/entity3-1-abc.webp"
    assert thumbnail_keys("originals/x.jpg") == [
        "thumbnails/64/x.webp",
        "thumbnails/160/x.webp",
        "thumbnails/320/x.webp",
        "thumbnails/640/x.webp",
        "thumbnails/960/x.webp",
        "thumbnails/1280/x.webp",
    ]
    assert thumbnail_stem("thumbnails/64/x.webp") == "x"
    assert thumbnail_stem("originals/x.png") is None
    assert is_original_key("originals/x.png")
    assert not is_original_key("originals/x.svg")
    assert not is_original_key("thumbnails/64/x.webp")
    assert not is_original_key("originals/../x.png")
    assert content_type_of("originals/x.jpeg") == "image/jpeg"
    assert content_type_of("originals/x.bin") == "application/octet-stream"
    assert is_sha256("a" * 64)
    assert not is_sha256("A" * 64)
    assert not is_sha256(None)


def test_endpoint_url() -> None:
    assert endpoint_url("", False) is None
    assert endpoint_url("minio:9000", False) == "http://minio:9000"
    assert endpoint_url("s3.example.org", True) == "https://s3.example.org"
    assert endpoint_url("https://s3.example.org/", False) == "https://s3.example.org"


def test_factory_picks_backend(tmp_path: Path) -> None:
    local = create_media_store(Settings(data_dir=tmp_path, media_backend=MediaBackend.FILE))
    assert isinstance(local, FileMediaStore)
    assert local.root == tmp_path / "media"
    remote_settings = Settings(
        data_dir=tmp_path,
        media_backend=MediaBackend.S3,
        media_endpoint="minio:9000",
        media_bucket="worlds",
        media_access_key="key",
        media_secret_key=SecretStr("secret-value"),
    )
    remote = create_media_store(remote_settings)
    assert isinstance(remote, S3MediaStore)
    assert remote.bucket == "worlds"
    config = s3_config(remote_settings)
    assert config.endpoint_url == "http://minio:9000"
    assert config.secret_key == "secret-value"


def test_settings_read_media_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AERONA_MEDIA_BACKEND", "s3")
    monkeypatch.setenv("AERONA_MEDIA_BUCKET", "from-env")
    monkeypatch.setenv("AERONA_MEDIA_SECURE", "true")
    configured = Settings(data_dir=tmp_path)
    assert configured.media_backend is MediaBackend.S3
    assert configured.media_bucket == "from-env"
    assert configured.media_secure


async def test_s3_store_creates_missing_bucket(s3_store: S3MediaStore) -> None:
    await s3_store.ensure_ready()
    await s3_store.put("originals/x.png", b"x")
    assert await s3_store.exists("originals/x.png")


async def test_file_store_skips_partial_writes(file_store: FileMediaStore) -> None:
    await file_store.put("originals/x.png", b"x")
    (file_store.root / "originals" / "x.png.abc.partial").write_bytes(b"half")
    assert [info.key async for info in file_store.list("originals/")] == ["originals/x.png"]
