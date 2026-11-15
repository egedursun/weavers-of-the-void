import asyncio
import hashlib
import logging
import os
import shutil
import tempfile
from collections.abc import AsyncIterator, Callable, Iterator
from pathlib import Path

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.orm import Session, UOWTransaction

from aerona.constants.media import MediaBackend
from aerona.db.migrations import SCRIPT_LOCATION, upgrade_to_head_sync
from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityType
from aerona.engine.pipeline import simulate
from aerona.main import create_app
from aerona.settings import Settings
from tests.engine.integration import factories
from tests.services.player import every_lever

STARTUP_SECONDS = 120
SCHEMA_CACHE = Path(tempfile.gettempdir()) / "aerona-schema"

type OpenDatabase = Callable[[Path], Database]


TOOL_RUNTIME_LOGGER = "aerona.tools.framework.runtime"


class SwallowedFailures(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.ERROR)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        if record.exc_info is not None:
            self.records.append(record)


@event.listens_for(Session, "before_flush")
def towns_hold_no_affiliation(session: Session, flush: UOWTransaction, instances: object) -> None:
    for row in [*session.new, *session.dirty]:
        if isinstance(row, EntityRow) and row.entity_type is EntityType.SETTLEMENT and row.affiliated_entity_id is not None:
            raise AssertionError(f"{row.name} is a settlement holding an affiliation; a town holds its people by a homeland bond")


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


def schema_digest() -> str:
    digest = hashlib.sha256()
    for script in sorted(SCRIPT_LOCATION.rglob("*.py")):
        digest.update(script.read_bytes())
    return digest.hexdigest()[:24]


@pytest.fixture(scope="session")
def schema_template() -> Path:
    cached = SCHEMA_CACHE / f"{schema_digest()}.db"
    if not cached.exists():
        SCHEMA_CACHE.mkdir(parents=True, exist_ok=True)
        building = SCHEMA_CACHE / f"{cached.stem}.{os.getpid()}.building"
        upgrade_to_head_sync(f"sqlite+aiosqlite:///{building}")
        os.replace(building, cached)
    return cached


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


LEVER_CACHE = Path(tempfile.gettempdir()) / "aerona-levers"
ENGINE_SOURCE = Path(__file__).resolve().parents[1] / "src" / "aerona"


def template_digest(schema_template: Path) -> str:
    digest = hashlib.sha256(schema_template.name.encode())
    for module in (factories, every_lever):
        digest.update(Path(module.__file__ or "").read_bytes())
    for path in sorted(ENGINE_SOURCE.rglob("*.py")):
        digest.update(path.read_bytes())
    return digest.hexdigest()[:24]


async def seed(path: Path) -> None:
    database = Database(f"sqlite+aiosqlite:///{path}")
    try:
        async with database.write() as session:
            await factories.seed_rich_cosmos(session)
        await simulate(database, 2)
    finally:
        await database.dispose()


@pytest.fixture(scope="session")
def lever_template(schema_template: Path) -> Path:
    cached = LEVER_CACHE / f"{template_digest(schema_template)}.db"
    if not cached.exists():
        LEVER_CACHE.mkdir(parents=True, exist_ok=True)
        building = LEVER_CACHE / f"{cached.stem}.{os.getpid()}.building"
        shutil.copyfile(schema_template, building)
        asyncio.run(seed(building))
        os.replace(building, cached)
    return cached
