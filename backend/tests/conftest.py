import asyncio
import fcntl
import hashlib
import logging
import os
import shutil
import tempfile
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import contextmanager
from dataclasses import replace
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
from aerona.db.write_guard import BOND_DOWNGRADES
from aerona.domain.enums.entity import EntityType
from aerona.engine.cosmos import maps
from aerona.engine.pipeline import simulate
from aerona.main import create_app
from aerona.rules.registry import Rules
from aerona.settings import Settings
from tests.engine.integration import factories
from tests.library_support import sign_in_owner, sole_universe, universe_headers
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


@pytest.fixture(autouse=True, scope="session")
def maps_drawn_in_the_test_worker() -> Iterator[None]:
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(maps, "workers_for", lambda _rules: 1)
        yield


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


@pytest.fixture(autouse=True)
def no_engine_bond_downgrades(request: pytest.FixtureRequest) -> Iterator[None]:
    downgrades: list[str] = []
    token = BOND_DOWNGRADES.set(downgrades)
    try:
        yield
    finally:
        BOND_DOWNGRADES.reset(token)
    if downgrades and request.node.get_closest_marker("bond_downgrade_expected") is None:
        pytest.fail(f"engine code asked for a bond its ends cannot hold and it fell back to a plain relation: {', '.join(sorted(set(downgrades)))}")


@contextmanager
def built_once(cached: Path) -> Iterator[bool]:
    cached.parent.mkdir(parents=True, exist_ok=True)
    with (cached.parent / f"{cached.stem}.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield not cached.exists()
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def schema_digest() -> str:
    digest = hashlib.sha256()
    for script in sorted(SCRIPT_LOCATION.rglob("*.py")):
        digest.update(script.read_bytes())
    return digest.hexdigest()[:24]


@pytest.fixture(scope="session")
def schema_template() -> Path:
    cached = SCHEMA_CACHE / f"{schema_digest()}.db"
    with built_once(cached) as missing:
        if missing:
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
def settings(tmp_path: Path, schema_template: Path) -> Settings:
    found = Settings(data_dir=tmp_path / "data", llm_enabled=False, image_worker_url="", work_in_processes=False)
    found.database_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(schema_template, found.database_path)
    return found


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings)
    async with LifespanManager(app, startup_timeout=STARTUP_SECONDS, shutdown_timeout=STARTUP_SECONDS) as manager:
        transport = ASGITransport(app=manager.app)
        headers = universe_headers(await sole_universe(app))
        async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as http:
            await sign_in_owner(app, http)
            yield http


LEVER_CACHE = Path(tempfile.gettempdir()) / "aerona-levers"
LEVER_RULES = replace(Rules(), healing=replace(Rules().healing, lethal_after_years=150))
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
        await simulate(database, 2, rules=LEVER_RULES)
    finally:
        await database.dispose()


@pytest.fixture(scope="session")
def lever_template(schema_template: Path) -> Path:
    cached = LEVER_CACHE / f"{template_digest(schema_template)}.db"
    with built_once(cached) as missing:
        if missing:
            building = LEVER_CACHE / f"{cached.stem}.{os.getpid()}.building"
            shutil.copyfile(schema_template, building)
            asyncio.run(seed(building))
            os.replace(building, cached)
    return cached
