from pathlib import Path

import pytest

from aerona.constants.media import MediaBackend
from aerona.media.errors import InvalidMediaKeyError
from aerona.media.factory import create_media_store
from aerona.media.file_store import FileMediaStore
from aerona.media.prefixed import PrefixedMediaStore
from aerona.media.s3_store import S3MediaStore
from aerona.media.store import list_keys, read_all
from aerona.settings import Settings

KEY = "originals/shared-name.png"


async def test_universes_sharing_one_bucket_never_see_each_others_objects(tmp_path: Path) -> None:
    bucket = FileMediaStore(tmp_path / "bucket")
    await bucket.ensure_ready()
    first = PrefixedMediaStore(bucket, "universes/aaaaaaaaaaa1/")
    second = PrefixedMediaStore(bucket, "universes/aaaaaaaaaaa2/")
    put = await first.put(KEY, b"first")
    assert put.key == KEY
    await second.put(KEY, b"second")
    await bucket.put(KEY, b"adopted")
    assert await read_all(first, KEY) == b"first"
    assert await read_all(second, KEY) == b"second"
    assert await read_all(bucket, KEY) == b"adopted"
    assert [info.key for info in await list_keys(first, "originals/")] == [KEY]
    assert [info.key for info in await list_keys(bucket, "originals/")] == [KEY]
    head = await second.head(KEY)
    assert head is not None
    assert head.key == KEY
    await second.delete(KEY)
    assert not await second.exists(KEY)
    assert await first.exists(KEY)
    with pytest.raises(InvalidMediaKeyError):
        PrefixedMediaStore(bucket, "universes/../")


def test_the_factory_scopes_only_a_shared_bucket(tmp_path: Path) -> None:
    root = Settings(data_dir=tmp_path / "data", llm_enabled=False)
    scoped = root.for_universe("aaaaaaaaaaa1", "universes/aaaaaaaaaaa1/")
    assert isinstance(create_media_store(scoped), FileMediaStore)
    shared = create_media_store(scoped.model_copy(update={"media_backend": MediaBackend.S3}))
    assert isinstance(shared, PrefixedMediaStore)
    adopted = create_media_store(root.for_universe("aaaaaaaaaaa2", "").model_copy(update={"media_backend": MediaBackend.S3}))
    assert isinstance(adopted, S3MediaStore)


def test_universe_settings_keep_process_paths_shared(tmp_path: Path) -> None:
    root = Settings(data_dir=tmp_path / "data", llm_enabled=False, secondary_backup_dir=tmp_path / "copies")
    scoped = root.for_universe("aaaaaaaaaaa1", "")
    assert scoped.data_dir == tmp_path / "data" / "universes" / "aaaaaaaaaaa1"
    assert scoped.log_file == root.log_file
    assert scoped.process.models == root.process.models
    assert scoped.process.library_database == root.process.library_database
    assert scoped.paths.work.parent == scoped.data_dir
    assert scoped.paths.forecasts.parent == scoped.data_dir
    assert scoped.paths.discovery_state.parent == scoped.data_dir
    assert scoped.secondary_backup_dir == tmp_path / "copies" / "aaaaaaaaaaa1"
