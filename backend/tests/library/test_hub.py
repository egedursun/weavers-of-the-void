import asyncio
import logging
from collections.abc import AsyncGenerator, AsyncIterator
from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy.orm import Session

from aerona.core.errors import BusyError, UniverseRequiredError
from aerona.domain.enums.job import JobKind
from aerona.domain.enums.library import UniverseOrigin, UniverseStatus
from aerona.engine.primitives.map_store import STORED
from aerona.events.bus import Event
from aerona.jobs.context import JobContext
from aerona.services.application import TRACKED_FEEDS
from aerona.services.library.adoption import prepare_library
from aerona.services.library.catalogue import Catalogue
from aerona.services.library.hub import UniverseHub
from aerona.services.library.runtime import UniverseRuntime
from aerona.services.metrics import ERROR_ROUTER
from aerona.settings import Settings
from tests.polling import until

SESSION_EVENTS = ("after_flush", "after_commit", "after_rollback", "before_flush", "do_orm_execute")
CYCLES = 4


def library_settings(tmp_path: Path, **overrides: Any) -> Settings:
    return Settings(data_dir=tmp_path / "data", llm_enabled=False, image_worker_url="", **overrides)


@pytest.fixture
async def hub(tmp_path: Path) -> AsyncIterator[UniverseHub]:
    settings = library_settings(tmp_path, library_open_universes=2)
    settings.ensure_process_directories()
    catalogue = Catalogue(settings.process)
    await prepare_library(catalogue)
    opened = UniverseHub(settings, catalogue)
    try:
        yield opened
    finally:
        await opened.stop()
        await catalogue.close()


async def hold_a_job(runtime: UniverseRuntime) -> tuple[str, asyncio.Event]:
    release = asyncio.Event()

    async def handler(_context: JobContext) -> dict[str, Any]:
        await release.wait()
        return {}

    job = await runtime.services.jobs.submit(JobKind.BOOK, handler)
    return job, release


def listener_counts() -> dict[str, int]:
    return {name: len(getattr(Session.dispatch, name)._clslevel[Session]) for name in SESSION_EVENTS}


async def test_a_new_universe_opens_at_the_schema_head_and_is_catalogued(hub: UniverseHub) -> None:
    record = await hub.create("Fresh shelf", notes="first", tags=("one",))
    assert record.origin is UniverseOrigin.CREATED
    assert record.media_prefix == f"universes/{record.id}/"
    assert record.schema_revision
    runtime = await hub.open(record.id)
    assert runtime.services.settings.universe_id == record.id
    assert runtime.services.settings.database_path == hub.paths_of(record.id).database
    assert runtime.services.settings.log_file == hub.settings.log_file
    assert (await hub.catalogue.require(record.id)).opened_at is not None


async def test_idle_close_waits_for_running_jobs_and_listeners(hub: UniverseHub, monkeypatch: pytest.MonkeyPatch) -> None:
    record = await hub.create("Busy shelf")
    runtime = await hub.open(record.id)
    job, release = await hold_a_job(runtime)
    monkeypatch.setattr(runtime, "used", runtime.used - hub.idle_seconds - 1)
    assert await hub.sweep() == []
    assert hub.is_open(record.id)
    with pytest.raises(BusyError):
        await hub.close(record.id)
    release.set()
    await runtime.services.jobs.get(job)
    assert await until(lambda: runtime.services.jobs.running_count == 0)
    stream = cast("AsyncGenerator[Event]", runtime.services.bus.subscribe())
    waiting = asyncio.ensure_future(anext(stream))
    await asyncio.sleep(0)
    assert runtime.busy_reason() is not None
    assert await hub.sweep() == []
    waiting.cancel()
    await asyncio.gather(waiting, return_exceptions=True)
    await stream.aclose()
    assert await hub.sweep() == [record.id]
    assert not hub.is_open(record.id)


async def test_the_least_recently_used_idle_universe_closes_first(hub: UniverseHub) -> None:
    first, second, third = [await hub.create(name) for name in ("One", "Two", "Three")]
    busy = await hub.open(first.id)
    _job, release = await hold_a_job(busy)
    await hub.open(second.id)
    await hub.open(third.id)
    assert set(hub.open_ids()) == {first.id, third.id}
    release.set()


async def test_archived_and_unknown_universes_refuse_to_open(hub: UniverseHub) -> None:
    record = await hub.create("Shelved")
    await hub.archive(record.id)
    assert (await hub.catalogue.require(record.id)).status is UniverseStatus.ARCHIVED
    with pytest.raises(UniverseRequiredError):
        await hub.acquire(record.id)
    with pytest.raises(UniverseRequiredError):
        await hub.acquire("nosuchshelf1")
    with pytest.raises(UniverseRequiredError):
        await hub.acquire("")
    await hub.restore(record.id)
    assert (await hub.acquire(record.id)).requests == 1


async def test_opening_and_closing_never_piles_up_listeners_or_handlers(hub: UniverseHub) -> None:
    record = await hub.create("Cycled")
    await hub.open(record.id)
    await hub.close(record.id)
    sessions = listener_counts()
    handlers = len(logging.getLogger().handlers)
    for _ in range(CYCLES):
        runtime = await hub.open(record.id)
        assert runtime.services.database.engine.sync_engine in TRACKED_FEEDS
        await hub.close(record.id)
    assert listener_counts() == sessions
    assert len(logging.getLogger().handlers) == handlers
    assert record.id not in ERROR_ROUTER.rings
    assert not any(str(hub.paths_of(record.id).database) in key[0] for key in STORED)


async def test_a_duplicate_carries_the_database_and_the_files(hub: UniverseHub) -> None:
    source = await hub.create("Original")
    runtime = await hub.open(source.id)
    await runtime.services.application.media.put("originals/kept.png", b"png bytes")
    copy = await hub.duplicate(source.id)
    assert copy.origin is UniverseOrigin.DUPLICATED
    assert copy.origin_note == source.id
    assert copy.name == "Original (2)"
    copied = await hub.open(copy.id)
    assert await copied.services.application.media.exists("originals/kept.png")
    assert copied.services.settings.database_path != runtime.services.settings.database_path
