import logging
import shutil
from collections.abc import AsyncIterator, Callable, Iterator
from pathlib import Path

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from aerona.constants.media import MediaBackend
from aerona.db.migrations import upgrade_to_head_sync
from aerona.db.session import Database
from aerona.main import create_app
from aerona.settings import Settings

STARTUP_SECONDS = 120

type OpenDatabase = Callable[[Path], Database]


TOOL_RUNTIME_LOGGER = "aerona.tools.framework.runtime"


class SwallowedFailures(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.ERROR)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        if record.exc_info is not None:
            self.records.append(record)


@pytest.fixture(autouse=True)
def local_media(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AERONA_MEDIA_BACKEND", MediaBackend.FILE.value)


@pytest.fixture(autouse=True)
def no_swallowed_tool_failures(request: pytest.FixtureRequest) -> Iterator[None]:
    handler = SwallowedFailures()
    logger = logging.getLogger(TOOL_RUNTIME_LOGGER)
    logger.addHandler(handler)
    try:
        yield
    finally:
        logger.removeHandler(handler)
    if handler.records and request.node.get_closest_marker("tool_failure_expected") is None:
        first = handler.records[0]
        assert first.exc_info is not None
        pytest.fail(f"a tool call crashed inside the runtime: {first.exc_info[0].__name__ if first.exc_info[0] else ''}: {first.exc_info[1]}")


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
    async with LifespanManager(app, startup_timeout=STARTUP_SECONDS, shutdown_timeout=STARTUP_SECONDS) as manager:
        transport = ASGITransport(app=manager.app)
        async with AsyncClient(transport=transport, base_url="http://test") as http:
            yield http
