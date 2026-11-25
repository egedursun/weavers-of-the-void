import asyncio
import json
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any, cast

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from aerona.api.routers.library import library_stream
from aerona.domain.enums.job import JobKind
from aerona.epoch.concurrency import WORLD_GROUP
from aerona.imaging.client import ImageWorkerClient
from aerona.jobs.context import JobContext
from aerona.main import create_app
from aerona.services.library.service import LibraryService
from aerona.settings import Settings
from tests.imaging.fake_worker import WORKER_URL, FakeWorker
from tests.library.shelf import LOCAL_ORIGIN, png
from tests.library_support import sole_universe

BASE_URL = "http://localhost"


class Shelf:
    def __init__(self, http: AsyncClient, app: FastAPI) -> None:
        self.http = http
        self.app = app

    @property
    def library(self) -> LibraryService:
        library: LibraryService = self.app.state.library
        return library

    async def create(self, name: str, **extra: Any) -> dict[str, Any]:
        response = await self.http.post("/api/library/universes", json={"name": name, **extra})
        assert response.status_code == 201, response.text
        return dict(response.json())


@pytest.fixture
async def shelf(settings: Settings) -> AsyncIterator[Shelf]:
    app = create_app(settings)
    async with (
        LifespanManager(app, startup_timeout=120, shutdown_timeout=120) as manager,
        AsyncClient(transport=ASGITransport(app=manager.app), base_url=BASE_URL) as http,
    ):
        yield Shelf(http, app)


async def test_library_routes_answer_without_a_universe(shelf: Shelf) -> None:
    listed = await shelf.http.get("/api/library/universes")
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert {item["value"]: item["count"] for item in body["facets"]["statuses"]} == {"active": 1, "archived": 0}
    assert (await shelf.http.get("/api/library/events")).status_code == 200
    assert (await shelf.http.get("/api/library/trash")).json()["total"] == 0
    assert (await shelf.http.get("/api/library/jobs")).json() == []
    assert (await shelf.http.get("/api/state")).json()["code"] == "universe_required"


async def test_create_edit_open_close_and_read_one(shelf: Shelf) -> None:
    created = await shelf.create("Second shelf", notes="first draft", tags=["sea", "Sea", "old"])
    assert created["origin"] == "created"
    assert created["tags"] == ["sea", "old"]
    taken = await shelf.create("Second shelf")
    assert taken["name"] == "Second shelf (2)"
    patched = await shelf.http.patch(f"/api/library/universes/{created['id']}", json={"name": "Renamed", "pinned": True, "summary": "A summary"})
    assert patched.status_code == 200
    assert patched.json()["pinned"] is True
    assert patched.json()["summary"] == "A summary"
    opened = (await shelf.http.post(f"/api/library/universes/{created['id']}/open")).json()
    assert opened["is_open"] is True
    assert opened["opened_at"] is not None
    state = await shelf.http.get("/api/state", headers={"X-Aerona-Universe": created["id"]})
    assert state.status_code == 200
    closed = (await shelf.http.post(f"/api/library/universes/{created['id']}/close")).json()
    assert closed["is_open"] is False
    detail = (await shelf.http.get(f"/api/library/universes/{created['id']}")).json()
    assert {event["kind"] for event in detail["events"]} >= {"created", "renamed", "opened"}
    sorted_by_name = (await shelf.http.get("/api/library/universes", params={"sort": "name"})).json()
    assert [item["name"] for item in sorted_by_name["items"]] == sorted(item["name"] for item in sorted_by_name["items"])
    found = (await shelf.http.get("/api/library/universes", params={"q": "renamed"})).json()
    assert [item["id"] for item in found["items"]] == [created["id"]]
    tagged = (await shelf.http.get("/api/library/universes", params={"tag": "OLD"})).json()
    assert [item["id"] for item in tagged["items"]] == [created["id"]]
    assert (await shelf.http.get("/api/library/universes/missing00000")).status_code == 404


async def test_duplicate_archive_and_restore(shelf: Shelf) -> None:
    source = await sole_universe(shelf.app)
    copy = await shelf.http.post(f"/api/library/universes/{source}/duplicate", json={"name": "Twin"})
    assert copy.status_code == 201, copy.text
    assert copy.json()["origin"] == "duplicated"
    assert copy.json()["origin_note"] == source
    archived = (await shelf.http.post(f"/api/library/universes/{copy.json()['id']}/archive")).json()
    assert archived["status"] == "archived"
    assert copy.json()["id"] not in {item["id"] for item in (await shelf.http.get("/api/library/universes")).json()["items"]}
    everything = (await shelf.http.get("/api/library/universes", params={"include_archived": True})).json()
    assert copy.json()["id"] in {item["id"] for item in everything["items"]}
    refused = await shelf.http.patch(f"/api/library/universes/{copy.json()['id']}", json={"name": "Locked"})
    assert refused.status_code == 409
    blocked = await shelf.http.get("/api/state", headers={"X-Aerona-Universe": copy.json()["id"]})
    assert blocked.json()["code"] == "universe_required"
    restored = await shelf.http.patch(f"/api/library/universes/{copy.json()['id']}", json={"status": "active"})
    assert restored.json()["status"] == "active"
    again = (await shelf.http.post(f"/api/library/universes/{copy.json()['id']}/archive")).json()
    back = (await shelf.http.post(f"/api/library/universes/{again['id']}/restore")).json()
    assert back["status"] == "active"


async def test_delete_moves_to_trash_and_the_trash_restores_and_purges(shelf: Shelf) -> None:
    first = await shelf.create("Doomed", tags=["kept"])
    gone = await shelf.http.delete(f"/api/library/universes/{first['id']}")
    assert gone.status_code == 200, gone.text
    entry = gone.json()
    assert entry["universe_id"] == first["id"]
    assert (await shelf.http.get(f"/api/library/universes/{first['id']}")).status_code == 404
    assert (await shelf.http.get("/api/library/trash")).json()["items"][0]["id"] == entry["id"]
    back = await shelf.http.post(f"/api/library/trash/{entry['id']}/restore")
    assert back.status_code == 200, back.text
    assert back.json()["id"] == first["id"]
    assert back.json()["tags"] == ["kept"]
    assert (await shelf.http.get("/api/library/trash")).json()["total"] == 0
    second = (await shelf.http.delete(f"/api/library/universes/{first['id']}")).json()
    purged = await shelf.http.delete(f"/api/library/trash/{second['id']}")
    assert purged.status_code == 200
    assert (await shelf.http.get("/api/library/trash")).json()["total"] == 0
    assert not (shelf.library.process.trash / second["id"]).exists()
    kinds = [event["kind"] for event in (await shelf.http.get("/api/library/events", params={"universe_id": first["id"]})).json()["items"]]
    assert kinds[:4] == ["purged", "deleted", "recovered", "deleted"]


async def test_the_whole_trash_is_emptied_at_once_and_its_weight_is_told(shelf: Shelf) -> None:
    sizes = []
    for name in ("First to go", "Second to go"):
        made = await shelf.create(name)
        sizes.append((await shelf.http.delete(f"/api/library/universes/{made['id']}")).json()["size_bytes"])
    listed = (await shelf.http.get("/api/library/trash", params={"limit": 1})).json()
    assert listed["total"] == 2
    assert listed["held_bytes"] == sum(sizes)
    assert listed["keep_days"] == shelf.library.settings.library_trash_days
    emptied = await shelf.http.delete("/api/library/trash")
    assert emptied.json() == {"purged": 2}
    after = (await shelf.http.get("/api/library/trash")).json()
    assert (after["total"], after["held_bytes"]) == (0, 0)
    assert not any(shelf.library.process.trash.iterdir())


async def test_an_unborn_universe_paints_from_its_summary_or_a_prompt_of_the_players_own(shelf: Shelf) -> None:
    made = await shelf.create("Riverlands", summary="a slow river that runs uphill")
    runtime = await shelf.library.hub.acquire(made["id"])
    worker = FakeWorker()
    runtime.services.application.images._client = ImageWorkerClient(WORKER_URL, transport=worker.transport())
    shelf.library.hub.release(runtime)
    default = await shelf.http.get(f"/api/library/universes/{made['id']}/cover/paint")
    assert default.json() == {"prompt": "a slow river that runs uphill"}
    painted = await shelf.http.post(f"/api/library/universes/{made['id']}/cover/paint", json={"prompt": "a gate of glass"})
    assert painted.status_code == 200, painted.text
    assert painted.headers["content-type"] == "image/png"
    assert painted.content == worker.image
    assert "a gate of glass" in worker.bodies[-1]["prompt"]
    assert (await shelf.http.post(f"/api/library/universes/{made['id']}/cover/paint", json={"prompt": ""})).status_code == 400


async def test_the_trash_is_emptied_after_its_days(shelf: Shelf, monkeypatch: pytest.MonkeyPatch) -> None:
    doomed = await shelf.create("Forgotten")
    entry = (await shelf.http.delete(f"/api/library/universes/{doomed['id']}")).json()
    assert await shelf.library.purge_expired() == []
    monkeypatch.setattr(shelf.library.settings, "library_trash_days", 0)
    assert await shelf.library.maintain() == [entry["id"]]
    assert (await shelf.http.get("/api/library/trash")).json()["total"] == 0


async def test_a_running_epoch_blocks_delete_and_archive(shelf: Shelf) -> None:
    universe = await sole_universe(shelf.app)
    runtime = await shelf.library.hub.open(universe)
    release = asyncio.Event()

    async def epoch(_context: JobContext) -> dict[str, Any]:
        await release.wait()
        return {}

    await runtime.services.jobs.submit(JobKind.EPOCH, epoch, exclusive_group=WORLD_GROUP)
    busy = (await shelf.http.get(f"/api/library/universes/{universe}")).json()
    assert busy["running_jobs"] == ["epoch"]
    deleted = await shelf.http.delete(f"/api/library/universes/{universe}")
    assert deleted.status_code == 409
    assert "an epoch is running" in deleted.json()["error"]
    archived = await shelf.http.post(f"/api/library/universes/{universe}/archive")
    assert archived.status_code == 409
    assert "an epoch is running" in archived.json()["error"]
    release.set()
    assert (await shelf.http.get(f"/api/library/universes/{universe}")).json()["status"] == "active"


async def test_a_cover_is_uploaded_read_and_cleared(shelf: Shelf) -> None:
    universe = await sole_universe(shelf.app)
    cover_url = f"/api/library/universes/{universe}/cover"
    refused = await shelf.http.put(cover_url, files={"file": ("cover.png", b"not an image", "image/png")}, headers=LOCAL_ORIGIN)
    assert refused.status_code == 400
    unsigned = await shelf.http.put(cover_url, files={"file": ("cover.png", png(), "image/png")})
    assert unsigned.status_code == 403
    put = await shelf.http.put(cover_url, files={"file": ("cover.png", png(), "image/png")}, headers=LOCAL_ORIGIN)
    assert put.status_code == 200, put.text
    assert put.json()["cover_path"] == "cover.png"
    cover = await shelf.http.get(cover_url)
    assert cover.content == png()
    cleared = (await shelf.http.delete(cover_url)).json()
    assert cleared["cover_path"] is None
    assert (await shelf.http.get(cover_url)).status_code == 404
    image_routes_unchanged = await shelf.http.put("/api/images/1/cover", json={}, headers={"X-Aerona-Universe": universe})
    assert image_routes_unchanged.status_code != 415


async def test_the_live_stream_says_hello_then_tells_every_change(shelf: Shelf) -> None:
    response = await library_stream(shelf.library)
    messages = cast(AsyncGenerator[dict[str, str]], response.body_iterator)
    hello = await anext(messages)
    assert hello["event"] == "hello"
    waiting = asyncio.ensure_future(anext(messages))
    await asyncio.sleep(0)
    created = await shelf.create("Watched")
    message = await asyncio.wait_for(waiting, timeout=10)
    event = json.loads(message["data"])
    assert event["kind"] == "universe"
    assert event["universe"]["id"] == created["id"]
    await messages.aclose()
