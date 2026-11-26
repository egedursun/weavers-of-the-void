import asyncio
import contextlib
import logging
import shutil
import sqlite3
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import replace
from typing import Any

from aerona.agents.ports import LanguageModel
from aerona.constants.app import APP_VERSION
from aerona.constants.library import IDLE_SWEEP_SECONDS, SECONDS_PER_MINUTE, UNIVERSE_MEDIA_PREFIX
from aerona.constants.media import ORIGINALS_PREFIX, THUMBNAILS_PREFIX
from aerona.core.errors import BusyError, UniverseRequiredError
from aerona.core.universe_scope import in_universe
from aerona.db.migrations import upgrade_to_head
from aerona.domain.enums.library import LibraryEventKind, UniverseOrigin, UniverseStatus
from aerona.events.bus import Event
from aerona.events.kinds import EventKind
from aerona.media.factory import create_media_store
from aerona.media.store import MediaStore, list_keys, read_all
from aerona.paths import UniversePaths
from aerona.services.container import Services
from aerona.services.divine_will.attachments import MEDIA_PREFIX as ATTACHMENT_PREFIX
from aerona.services.library.catalogue import Catalogue, NewUniverse, UniverseEdit, UniverseRecord, new_universe_id
from aerona.services.library.facts import facts_at, facts_of, schema_revision_at
from aerona.services.library.runtime import UniverseRuntime, close_services, launch_services
from aerona.services.providers.hub import Providers
from aerona.settings import Settings

logger = logging.getLogger(__name__)

Launcher = Callable[..., Awaitable[Services]]
Closer = Callable[[Services], Awaitable[None]]
OpenedHook = Callable[[UniverseRuntime], Awaitable[None]]
ClosedHook = Callable[[str], Awaitable[None]]
RefreshedHook = Callable[[UniverseRecord], Awaitable[None]]

CHOOSE_UNIVERSE = "Choose a universe in the library first."
UNKNOWN_UNIVERSE = "That universe is not in the library."
ARCHIVED_UNIVERSE = "That universe is archived; restore it in the library to open it."
STILL_BUSY = "The universe cannot be closed while {reason}."
COPIED_PREFIXES = (ORIGINALS_PREFIX, THUMBNAILS_PREFIX, f"{ATTACHMENT_PREFIX}/")
REFRESH_KINDS = frozenset({EventKind.EPOCH_FINISHED, EventKind.WORLD_REPLACED})


def copy_database(source: UniversePaths, target: UniversePaths) -> None:
    target.root.mkdir(parents=True, exist_ok=True)
    reader = sqlite3.connect(source.database)
    writer = sqlite3.connect(target.database)
    try:
        reader.backup(writer)
    finally:
        writer.close()
        reader.close()


def copy_cover(source: UniversePaths, target: UniversePaths, cover_path: str | None) -> str | None:
    if not cover_path:
        return None
    found = (source.root / cover_path).resolve()
    if not found.is_file() or not found.is_relative_to(source.root.resolve()):
        return None
    placed = target.root / found.relative_to(source.root.resolve())
    placed.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(found, placed)
    return cover_path


async def copy_media(source: MediaStore, target: MediaStore, prefixes: Iterable[str] = COPIED_PREFIXES) -> int:
    copied = 0
    for prefix in prefixes:
        for info in await list_keys(source, prefix):
            data = await read_all(source, info.key)
            if data is not None:
                await target.put(info.key, data)
                copied += 1
    return copied


class UniverseHub:
    def __init__(
        self,
        settings: Settings,
        catalogue: Catalogue,
        model: LanguageModel | None = None,
        *,
        launcher: Launcher = launch_services,
        closer: Closer = close_services,
        providers: Providers | None = None,
    ) -> None:
        self.settings = settings
        self.catalogue = catalogue
        self.model = model
        self.providers = providers
        self.slots = asyncio.Semaphore(settings.library_parallel_epochs)
        self.opened_hooks: list[OpenedHook] = []
        self.closed_hooks: list[ClosedHook] = []
        self.refreshed_hooks: list[RefreshedHook] = []
        self._launcher = launcher
        self._closer = closer
        self._runtimes: OrderedDict[str, UniverseRuntime] = OrderedDict()
        self._locks: dict[str, asyncio.Lock] = {}
        self._tasks: set[asyncio.Task[Any]] = set()
        self._sweeper: asyncio.Task[None] | None = None

    @property
    def idle_seconds(self) -> float:
        return self.settings.library_idle_minutes * SECONDS_PER_MINUTE

    @property
    def limit(self) -> int:
        return self.settings.library_open_universes

    def paths_of(self, universe_id: str) -> UniversePaths:
        return self.settings.process.universe(universe_id)

    def settings_of(self, record: UniverseRecord) -> Settings:
        return self.settings.for_universe(record.id, record.media_prefix)

    def runtime(self, universe_id: str) -> UniverseRuntime | None:
        return self._runtimes.get(universe_id)

    def open_ids(self) -> list[str]:
        return list(self._runtimes)

    def is_open(self, universe_id: str) -> bool:
        return universe_id in self._runtimes

    def running_jobs(self, universe_id: str) -> int:
        found = self._runtimes.get(universe_id)
        return found.services.jobs.running_count if found is not None else 0

    def running_jobs_total(self) -> int:
        return sum(runtime.services.jobs.running_count for runtime in self._runtimes.values())

    def busy_reason(self, universe_id: str) -> str | None:
        found = self._runtimes.get(universe_id)
        return found.busy_reason() if found is not None else None

    def _lock(self, universe_id: str) -> asyncio.Lock:
        return self._locks.setdefault(universe_id, asyncio.Lock())

    async def start(self) -> None:
        if self._sweeper is None:
            self._sweeper = asyncio.get_running_loop().create_task(self._sweep_forever())

    async def stop(self) -> None:
        if self._sweeper is not None:
            self._sweeper.cancel()
            await asyncio.gather(self._sweeper, return_exceptions=True)
            self._sweeper = None
        for universe_id in list(self._runtimes):
            await self.close(universe_id, force=True)
        for task in list(self._tasks):
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def admitted(self, universe_id: str) -> UniverseRecord:
        if not universe_id:
            raise UniverseRequiredError(CHOOSE_UNIVERSE)
        record = await self.catalogue.get(universe_id)
        if record is None:
            raise UniverseRequiredError(UNKNOWN_UNIVERSE)
        if record.status is UniverseStatus.ARCHIVED:
            raise UniverseRequiredError(ARCHIVED_UNIVERSE)
        return record

    async def open(self, universe_id: str) -> UniverseRuntime:
        record = await self.admitted(universe_id)
        async with self._lock(universe_id):
            runtime = await self._ensure(record)
        await self.catalogue.mark_opened(universe_id)
        return runtime

    async def acquire(self, universe_id: str) -> UniverseRuntime:
        record = await self.admitted(universe_id)
        async with self._lock(universe_id):
            runtime = await self._ensure(record)
            runtime.requests += 1
        return runtime

    def release(self, runtime: UniverseRuntime) -> None:
        runtime.requests = max(0, runtime.requests - 1)
        runtime.touch()

    async def _ensure(self, record: UniverseRecord) -> UniverseRuntime:
        found = self._runtimes.get(record.id)
        if found is not None:
            self._runtimes.move_to_end(record.id)
            found.touch()
            return found
        await self._make_room(record.id)
        if self.providers is not None:
            self.providers.directory.place(record.id, record.workspace_id)
        with in_universe(record.id):
            services = await self._launcher(self.settings_of(record), self.model, slots=self.slots, providers=self.providers)
        runtime = UniverseRuntime(record.id, services)
        services.bus.add_listener(self._watcher(record.id))
        self._runtimes[record.id] = runtime
        for hook in self.opened_hooks:
            await hook(runtime)
        return runtime

    async def _make_room(self, keep: str) -> None:
        while len(self._runtimes) >= self.limit:
            idle = [runtime for runtime in self._runtimes.values() if runtime.universe_id != keep and runtime.busy_reason() is None]
            if not idle:
                logger.warning("every open universe is busy; opening one more than the limit of %s", self.limit)
                return
            await self.close(idle[0].universe_id)

    async def close(self, universe_id: str, *, force: bool = False) -> bool:
        async with self._lock(universe_id):
            runtime = self._runtimes.get(universe_id)
            if runtime is None:
                return False
            reason = runtime.busy_reason()
            if reason is not None and not force:
                raise BusyError(STILL_BUSY.format(reason=reason))
            del self._runtimes[universe_id]
            with in_universe(universe_id):
                await self._closer(runtime.services)
        await self.refresh(universe_id)
        for hook in self.closed_hooks:
            await hook(universe_id)
        return True

    async def sweep(self) -> list[str]:
        closed: list[str] = []
        for runtime in list(self._runtimes.values()):
            if runtime.idle_for() >= self.idle_seconds and runtime.busy_reason() is None:
                with contextlib.suppress(BusyError):
                    if await self.close(runtime.universe_id):
                        closed.append(runtime.universe_id)
        return closed

    async def _sweep_forever(self) -> None:
        interval = max(0.05, min(IDLE_SWEEP_SECONDS, self.idle_seconds / 2))
        while True:
            await asyncio.sleep(interval)
            try:
                await self.sweep()
            except Exception:
                logger.exception("the idle universes could not be closed")

    def _watcher(self, universe_id: str) -> Callable[[Event], None]:
        def watch(event: Event) -> None:
            if event.kind in REFRESH_KINDS:
                self._spawn(self.refresh(universe_id))

        return watch

    def _spawn(self, work: Awaitable[Any]) -> None:
        task = asyncio.ensure_future(work)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def refresh(self, universe_id: str) -> UniverseRecord | None:
        paths = self.paths_of(universe_id)
        runtime = self._runtimes.get(universe_id)
        try:
            facts = await facts_of(runtime.services.database, paths) if runtime is not None else await facts_at(paths)
        except Exception:
            logger.warning("the facts of universe %s could not be refreshed", universe_id, exc_info=True)
            return None
        record = await self.catalogue.store_facts(universe_id, facts) if facts is not None else None
        if record is not None:
            for hook in self.refreshed_hooks:
                await hook(record)
        return record

    async def fresh_id(self) -> str:
        while True:
            candidate = new_universe_id()
            if await self.catalogue.get(candidate) is None and not self.paths_of(candidate).root.exists():
                return candidate

    def media_prefix_of(self, universe_id: str) -> str:
        return UNIVERSE_MEDIA_PREFIX.format(universe_id=universe_id)

    async def register(self, universe_id: str, new: NewUniverse, kind: LibraryEventKind, detail: str = "") -> UniverseRecord:
        paths = self.paths_of(universe_id)
        await upgrade_to_head(f"sqlite+aiosqlite:///{paths.database}")
        record = await self.catalogue.add(universe_id, replace(new, schema_revision=await schema_revision_at(paths)))
        await self.catalogue.log(kind, universe_id, record.name, detail)
        return await self.refresh(universe_id) or record

    async def create(self, name: str, *, notes: str = "", tags: tuple[str, ...] = (), summary: str = "") -> UniverseRecord:
        universe_id = await self.fresh_id()
        self.paths_of(universe_id).root.mkdir(parents=True)
        new = NewUniverse(
            name=name,
            origin=UniverseOrigin.CREATED,
            media_prefix=self.media_prefix_of(universe_id),
            app_version=APP_VERSION,
            notes=notes,
            summary=summary,
            tags=tags,
        )
        return await self.register(universe_id, new, LibraryEventKind.CREATED)

    async def duplicate(self, source_id: str, name: str | None = None) -> UniverseRecord:
        source = await self.catalogue.require(source_id)
        universe_id = await self.fresh_id()
        origin, target = self.paths_of(source_id), self.paths_of(universe_id)
        await asyncio.to_thread(copy_database, origin, target)
        prefix = self.media_prefix_of(universe_id)
        await self._copy_media(source, self.settings.for_universe(universe_id, prefix))
        cover = await asyncio.to_thread(copy_cover, origin, target, source.cover_path)
        new = NewUniverse(
            name=await self.catalogue.free_name(name or source.name),
            origin=UniverseOrigin.DUPLICATED,
            media_prefix=prefix,
            app_version=APP_VERSION,
            notes=source.notes,
            summary=source.summary,
            origin_note=source.id,
            tags=source.tags,
        )
        record = await self.register(universe_id, new, LibraryEventKind.DUPLICATED, source.id)
        return await self.catalogue.edit(universe_id, UniverseEdit(cover_path=cover)) if cover is not None else record

    async def _copy_media(self, source: UniverseRecord, target_settings: Settings) -> int:
        running = self._runtimes.get(source.id)
        source_store = running.services.application.media if running is not None else create_media_store(self.settings_of(source))
        target_store = create_media_store(target_settings)
        try:
            await source_store.ensure_ready()
            await target_store.ensure_ready()
            return await copy_media(source_store, target_store)
        finally:
            await target_store.close()
            if running is None:
                await source_store.close()

    async def archive(self, universe_id: str) -> UniverseRecord:
        await self.catalogue.require(universe_id)
        await self.close(universe_id)
        return await self.catalogue.set_status(universe_id, UniverseStatus.ARCHIVED)

    async def restore(self, universe_id: str) -> UniverseRecord:
        await self.catalogue.require(universe_id)
        return await self.catalogue.set_status(universe_id, UniverseStatus.ACTIVE)
