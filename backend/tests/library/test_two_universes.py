import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from aerona.api.routers.books import TERRAIN_CACHE
from aerona.constants.library import UNIVERSE_HEADER, UNIVERSE_QUERY
from aerona.core.universe_scope import in_universe
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.domain.enums.job import JobKind
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.events.kinds import EventKind
from aerona.jobs.context import JobContext
from aerona.main import create_app
from aerona.services.container import Services
from aerona.services.library.hub import UniverseHub
from aerona.settings import Settings
from tests.agents.world import seed_agent_world
from tests.library_support import hub_of, sole_universe, universe_headers

STARTUP_SECONDS = 120
NOTE = "a note kept in the first universe"


@dataclass
class Shelf:
    http: AsyncClient
    hub: UniverseHub
    first: str
    second: str

    def services(self, universe_id: str) -> Services:
        runtime = self.hub.runtime(universe_id)
        assert runtime is not None
        return runtime.services

    async def get(self, universe_id: str, path: str, **params: Any) -> Any:
        response = await self.http.get(path, params=params, headers=universe_headers(universe_id))
        assert response.status_code == 200, response.text
        return response.json()


@pytest.fixture
async def shelf(settings: Settings) -> AsyncIterator[Shelf]:
    app = create_app(settings)
    async with LifespanManager(app, startup_timeout=STARTUP_SECONDS, shutdown_timeout=STARTUP_SECONDS) as manager:
        hub = hub_of(app)
        first = await sole_universe(app)
        second = (await hub.create("Second shelf")).id
        opened = await hub.open(first)
        await hub.open(second)
        async with opened.services.database.write() as session:
            await seed_agent_world(session, opened.services.rules.current)
        async with AsyncClient(transport=ASGITransport(app=manager.app), base_url="http://localhost") as http:
            yield Shelf(http=http, hub=hub, first=first, second=second)


async def test_records_events_jobs_and_files_stay_in_their_universe(shelf: Shelf) -> None:
    first, second = shelf.services(shelf.first), shelf.services(shelf.second)
    assert (await shelf.get(shelf.first, "/api/state"))["world"] is not None
    assert (await shelf.get(shelf.second, "/api/state"))["world"] is None
    first.bus.publish(EventKind.SYSTEM_NOTE, {"text": NOTE})
    texts = [item["payload"].get("text") for item in await shelf.get(shelf.second, "/api/activity-log")]
    assert NOTE not in texts
    assert NOTE in [item["payload"].get("text") for item in await shelf.get(shelf.first, "/api/activity-log")]
    release = asyncio.Event()

    async def held(_context: JobContext) -> dict[str, Any]:
        await release.wait()
        return {}

    job = await first.jobs.submit(JobKind.EPOCH, held, exclusive_group=WORLD_GROUP)
    assert second.jobs.running_count == 0
    assert [row["id"] for row in await shelf.get(shelf.second, "/api/jobs")] == []
    async with asyncio.timeout(5):
        assert (await shelf.get(shelf.second, "/api/state"))["world"] is None
    assert job in [row["id"] for row in await shelf.get(shelf.first, "/api/jobs")]
    release.set()
    paths = {first.settings.database_path, second.settings.database_path}
    assert len(paths) == 2
    assert all(path.parent.parent.name == "universes" for path in paths)
    await first.application.media.put("originals/only-first.png", b"first")
    assert not await second.application.media.exists("originals/only-first.png")
    assert first.application.feed is not second.application.feed


async def test_errors_and_caches_are_kept_per_universe(shelf: Shelf) -> None:
    first, second = shelf.services(shelf.first), shelf.services(shelf.second)
    with in_universe(shelf.first):
        logging.getLogger("aerona.test").warning("first universe trouble")
    assert any("first universe trouble" in entry.text for entry in first.application.errors.recent(10))
    assert not any("first universe trouble" in entry.text for entry in second.application.errors.recent(10))
    before = (first.application.feed.version, second.application.feed.version)
    async with first.database.write() as session:
        cosmos = await CosmosRepository(session).require_cosmos()
        cosmos.name = "A renamed cosmos"
    assert first.application.feed.version != before[0]
    assert second.application.feed.version == before[1]
    TERRAIN_CACHE.clear()
    map_of_first = await shelf.http.get("/api/book/maps/1.jpg", headers=universe_headers(shelf.first))
    if map_of_first.status_code == 200:
        assert all(key[0] == shelf.first for key in TERRAIN_CACHE)


async def test_a_request_must_name_a_known_open_universe(shelf: Shelf) -> None:
    missing = await shelf.http.get("/api/state")
    assert missing.status_code == 409
    assert missing.json()["code"] == "universe_required"
    unknown = await shelf.http.get("/api/state", headers={UNIVERSE_HEADER: "nosuchshelf1"})
    assert unknown.status_code == 409
    assert unknown.json()["code"] == "universe_required"
    await shelf.hub.archive(shelf.second)
    archived = await shelf.http.get("/api/state", headers=universe_headers(shelf.second))
    assert archived.status_code == 409
    assert archived.json()["code"] == "universe_required"
    by_query = await shelf.http.get("/api/state", params={UNIVERSE_QUERY: shelf.first})
    assert by_query.status_code == 200
    assert (await shelf.http.get("/api/health")).status_code == 200
    library = await shelf.http.get("/api/library/universes")
    assert library.status_code != 409
    writes = await shelf.http.post("/api/world/reset", json={"confirm": "RESET"})
    assert writes.status_code == 409
