import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.domain.enums.library import UniverseOrigin
from aerona.main import create_app
from aerona.media.keys import original_key
from aerona.paths import ProcessPaths
from aerona.services.library.catalogue import Catalogue, UniverseRecord
from aerona.settings import Settings
from tests.api.conftest import ApiWorld, open_api, seeded
from tests.library.shelf import (
    LOCAL_ORIGIN,
    database_with,
    exported,
    imported,
    members_of,
    packed,
    png,
    relisted,
    replaced,
    settled,
    table_digests,
    tree_of,
    uploaded,
)
from tests.library_support import sign_in_owner

ATTACHMENT_KEY = "divine-will/0123456789abcdef/notes.md"


@pytest.fixture
async def world(settings: Settings) -> AsyncIterator[ApiWorld]:
    async for opened in open_api(settings, seeded=True):
        yield opened


def process_of(world: ApiWorld) -> ProcessPaths:
    return world.services.settings.process


async def catalogued(world: ApiWorld, universe_id: str) -> UniverseRecord:
    catalogue = Catalogue(process_of(world))
    try:
        return await catalogue.require(universe_id)
    finally:
        await catalogue.close()


def left_behind(world: ApiWorld) -> list[str]:
    process = process_of(world)
    return sorted(path.name for folder in (process.imports,) if folder.is_dir() for path in folder.iterdir())


def shelf(world: ApiWorld) -> list[str]:
    folder = process_of(world).universes
    return sorted(path.name for path in folder.iterdir())


async def with_media(world: ApiWorld) -> str:
    town = seeded(world).core.extra["town"].id
    response = await world.http.post("/api/images", params={"node_id": town}, content=png(), headers={"content-type": "image/png"})
    assert response.status_code == 200, response.text
    await world.services.application.media.put(ATTACHMENT_KEY, b"a note the player brought")
    return str(response.json()["file_name"])


async def test_export_then_import_yields_the_same_database_and_media(world: ApiWorld, tmp_path: Path) -> None:
    await with_media(world)
    package = await exported(world.http, world.universe_id)
    members = dict(members_of(package))
    library = json.loads(members["library.json"])
    assert library["universe_id"] == world.universe_id
    assert {item["path"] for item in library["files"]} >= {"world.db", f"media/{ATTACHMENT_KEY}"}
    assert members_of(package)[0][0] == "manifest.json"
    snapshot = tmp_path / "snapshot.db"
    snapshot.write_bytes(members["world.db"])
    done = await imported(world.http, package, name="Shared shelf")
    assert done["universe_name"] == "Shared shelf"
    process = process_of(world)
    record = await catalogued(world, done["universe_id"])
    assert record.origin is UniverseOrigin.IMPORTED
    assert record.media_prefix == f"universes/{record.id}/"
    assert table_digests(process.universe(record.id).database) == table_digests(snapshot)
    source_media = tree_of(process.universe(world.universe_id).media)
    copied = tree_of(process.universe(record.id).media)
    kept = {key: body for key, body in source_media.items() if key.startswith(("originals/", "divine-will/"))}
    assert kept
    assert {key: body for key, body in copied.items() if key.startswith(("originals/", "divine-will/"))} == kept
    assert left_behind(world) == []


async def test_the_manifest_is_shown_before_the_import_is_confirmed(world: ApiWorld) -> None:
    package = await exported(world.http, world.universe_id)
    before = shelf(world)
    checked = await uploaded(world.http, package)
    assert checked["status"] == "waiting"
    preview = checked["preview"]
    assert preview["legacy"] is False
    assert preview["source_id"] == world.universe_id
    assert preview["schema_revision"]
    assert checked["universe_name"].endswith(" (2)")
    assert shelf(world) == before
    cancelled = await world.http.delete(f"/api/library/imports/{checked['id']}")
    assert cancelled.json()["status"] == "cancelled"
    assert left_behind(world) == []
    assert shelf(world) == before


async def refused(world: ApiWorld, data: bytes, words: str) -> None:
    before = shelf(world)
    checked = await uploaded(world.http, data)
    assert checked["status"] == "failed", checked
    assert words in checked["error"]
    assert left_behind(world) == []
    assert shelf(world) == before


async def test_a_tampered_file_is_refused_and_leaves_nothing(world: ApiWorld) -> None:
    members = members_of(await exported(world.http, world.universe_id))
    database = dict(members)["world.db"]
    await refused(world, packed(replaced(members, "world.db", database[:-1] + bytes([database[-1] ^ 1]))), "does not match")


async def test_a_path_that_leaves_the_package_is_refused(world: ApiWorld) -> None:
    members = members_of(await exported(world.http, world.universe_id))
    await refused(world, packed([*members, ("../outside.txt", b"escape")]), "leaves the package")
    await refused(world, packed([*members, ("media/../../outside.png", b"escape")]), "leaves the package")


async def test_a_schema_newer_than_this_edition_is_refused(world: ApiWorld, tmp_path: Path) -> None:
    members = members_of(await exported(world.http, world.universe_id))
    newer = database_with(dict(members)["world.db"], tmp_path, "UPDATE alembic_version SET version_num = 'ffffffffffff'")
    await refused(world, packed(relisted(replaced(members, "world.db", newer))), "newer edition")


async def test_a_corrupt_database_is_refused(world: ApiWorld) -> None:
    members = members_of(await exported(world.http, world.universe_id))
    await refused(world, packed(relisted(replaced(members, "world.db", b"SQLite format 3\x00" + b"\x07" * 8192))), "corrupt")


async def test_garbage_is_refused(world: ApiWorld) -> None:
    await refused(world, b"not a package at all", "could not be opened")


async def test_a_plain_world_export_from_before_the_library_imports(world: ApiWorld) -> None:
    await with_media(world)
    response = await world.http.get("/api/world/export")
    assert response.status_code == 200
    plain = response.content
    assert "library.json" not in dict(members_of(plain))
    checked = await uploaded(world.http, plain, "old.aerona")
    assert checked["status"] == "waiting", checked
    assert checked["preview"]["legacy"] is True
    done = await imported(world.http, plain)
    record = await catalogued(world, done["universe_id"])
    copied = tree_of(process_of(world).universe(record.id).media)
    assert any(key.startswith("originals/") for key in copied)
    assert record.origin_note == "shared.aerona"


async def test_an_oversized_upload_is_refused_before_anything_is_written(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "data", llm_enabled=False, image_worker_url="", library_import_max_mb=1)
    app = create_app(settings)
    async with (
        LifespanManager(app, startup_timeout=120, shutdown_timeout=120) as manager,
        AsyncClient(transport=ASGITransport(app=manager.app), base_url="http://localhost") as http,
    ):
        await sign_in_owner(app, http)
        response = await http.post("/api/library/imports", files={"file": ("big.aerona", b"x" * (3 * 1024 * 1024))}, headers=LOCAL_ORIGIN)
        assert response.status_code == 413
        process = settings.process
        assert not any(process.imports.iterdir()) if process.imports.is_dir() else True
        assert (await http.get("/api/library/universes")).json()["total"] == 0


async def test_an_upload_from_another_page_is_refused(world: ApiWorld) -> None:
    response = await world.http.post("/api/library/imports", files={"file": ("a.aerona", b"x")})
    assert response.status_code == 403
    foreign = await world.http.post("/api/library/imports", files={"file": ("a.aerona", b"x")}, headers={"origin": "https://elsewhere.example"})
    assert foreign.status_code == 403


async def test_a_cover_can_be_taken_from_the_universe_images(world: ApiWorld) -> None:
    file_name = await with_media(world)
    assert original_key(file_name)
    response = await world.http.put(f"/api/library/universes/{world.universe_id}/cover/from-media", json={"file_name": file_name})
    assert response.status_code == 200, response.text
    assert response.json()["cover_path"] == "cover.png"
    cover = await world.http.get(f"/api/library/universes/{world.universe_id}/cover")
    assert cover.status_code == 200
    assert cover.headers["content-type"] == "image/png"
    missing = await world.http.put(f"/api/library/universes/{world.universe_id}/cover/from-media", json={"file_name": "absent.png"})
    assert missing.status_code == 404


async def test_a_discarded_export_leaves_the_work_in_hand_and_its_file_is_gone(world: ApiWorld) -> None:
    job = (await world.http.post(f"/api/library/universes/{world.universe_id}/export")).json()
    finished = await settled(world.http, f"/api/library/exports/{job['id']}")
    assert finished["status"] == "done"
    discarded = await world.http.delete(f"/api/library/exports/{job['id']}")
    assert discarded.status_code == 200, discarded.text
    listed = (await world.http.get("/api/library/jobs")).json()
    assert job["id"] not in [held["id"] for held in listed]
    assert (await world.http.get(f"/api/library/exports/{job['id']}")).status_code == 404
    assert (await world.http.get(f"/api/library/exports/{job['id']}/file")).status_code == 404


async def test_a_refused_import_can_be_cleared_from_the_work_in_hand(world: ApiWorld) -> None:
    refused = await uploaded(world.http, b"not a universe at all")
    assert refused["status"] == "failed"
    cleared = await world.http.delete(f"/api/library/imports/{refused['id']}")
    assert cleared.status_code == 200, cleared.text
    listed = (await world.http.get("/api/library/jobs")).json()
    assert refused["id"] not in [held["id"] for held in listed]


async def test_a_born_universe_offers_its_own_seed_to_paint_its_cover(world: ApiWorld) -> None:
    async with world.services.database.read() as session:
        cosmos = await CosmosRepository(session).get()
    assert cosmos is not None and cosmos.seed_idea
    offered = (await world.http.get(f"/api/library/universes/{world.universe_id}/cover/paint")).json()
    assert offered == {"prompt": " ".join(cosmos.seed_idea.split())}
