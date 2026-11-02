import shutil
from collections.abc import AsyncIterator, Callable
from pathlib import Path

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from aerona.constants.media import MediaBackend
from aerona.db.migrations import upgrade_to_head_sync
from aerona.db.session import Database
from aerona.main import create_app
from aerona.settings import Settings

type OpenDatabase = Callable[[Path], Database]


@pytest.fixture(autouse=True)
def local_media(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AERONA_MEDIA_BACKEND", MediaBackend.FILE.value)


@pytest.fixture(scope="session")
def schema_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("schema") / "schema.db"
    upgrade_to_head_sync(f"sqlite+aiosqlite:///{path}")
    return path


@pytest.fixture
def open_database(schema_template: Path) -> OpenDatabase:
    def migrated(path: Path) -> Database:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(schema_template, path)
        return Database(f"sqlite+aiosqlite:///{path}")

    return migrated


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", llm_enabled=False, image_worker_url="")


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings)
    async with LifespanManager(app) as manager:
        transport = ASGITransport(app=manager.app)
        async with AsyncClient(transport=transport, base_url="http://test") as http:
            yield http
