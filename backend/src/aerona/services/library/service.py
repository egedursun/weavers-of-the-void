import asyncio
import logging
import secrets
import shutil
from collections import Counter
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from aerona.constants.api import MEGABYTE
from aerona.constants.library import COVER_PROMPT_MAX_LENGTH, LIBRARY_PAGE_DEFAULT
from aerona.constants.library_packages import (
    COVER_STEM,
    LIBRARY_JOB_ID_BYTES,
    LIBRARY_MAINTENANCE_SECONDS,
    LIBRARY_RECENT_EVENTS,
    PACKAGE_INFLATE_FACTOR,
    SECONDS_PER_DAY,
    UPLOAD_FILENAME,
    UPLOAD_NAME_MAX_LENGTH,
)
from aerona.constants.media import MediaBackend
from aerona.core.errors import BusyError, ConflictError, NotFoundError, ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.domain.enums.job import JobKind
from aerona.domain.enums.library import LibraryEventKind, UniverseStatus
from aerona.domain.enums.library_jobs import LibraryJobKind, LibraryJobStage, LibraryJobStatus, LibraryStreamKind
from aerona.domain.enums.meta import ImageMime
from aerona.media.factory import create_media_store
from aerona.media.keys import is_original_key, original_key
from aerona.media.store import list_keys, read_all
from aerona.services.images.records import EXTENSIONS, detect_mime
from aerona.services.library.catalogue import LibraryEventRecord, UniverseEdit, UniverseRecord
from aerona.services.library.feed import LibraryFeed
from aerona.services.library.hub import COPIED_PREFIXES, UniverseHub
from aerona.services.library.jobs import LibraryJob, LibraryJobs, remove_quietly
from aerona.services.library.package import CheckedPackage, check_package
from aerona.services.library.runtime import UniverseRuntime
from aerona.services.library.transfer import export_universe, media_of, place_package, threadsafe
from aerona.services.library.trash import TrashEntry, bring_back, find_entry, move_to_trash, trash_entries

logger = logging.getLogger(__name__)

ARCHIVED_READ_ONLY = "That universe is archived; restore it before changing it."
DELETE_BLOCKED = "The universe cannot be deleted while {reason}."
ARCHIVE_BLOCKED = "The universe cannot be archived while {reason}."
NOT_WAITING = "That import is not waiting for a name; it is {status}."
EMPTY_UPLOAD = "The file is empty."
TOO_LARGE = "The file is larger than the import limit of {limit} MB."
UNCHECKED = "The file could not be checked."
UNPLACED = "The universe could not be added to the library."
UNEXPORTED = "The universe could not be exported."
NOT_AN_IMAGE = "A cover must be a PNG, JPEG or WEBP image."
NO_COVER = "This universe has no cover."
NO_SUCH_IMAGE = "This universe holds no such image."
NO_EXPORT_FILE = "That export has no file to download yet."
UNNAMED_IMPORT = "Imported universe"


def upload_note(file_name: str) -> str:
    return " ".join(file_name.split())[:UPLOAD_NAME_MAX_LENGTH]


def mime_of(data: bytes) -> ImageMime | None:
    return next((mime for mime in ImageMime if detect_mime(data, mime)), None)


class LibraryService:
    def __init__(self, hub: UniverseHub) -> None:
        self.hub = hub
        self.catalogue = hub.catalogue
        self.settings = hub.settings
        self.process = hub.settings.process
        self.feed = LibraryFeed()
        self.jobs = LibraryJobs(self.feed)
        self._checked: dict[str, CheckedPackage] = {}
        self._loop: asyncio.Task[None] | None = None
        hub.opened_hooks.append(self._opened)
        hub.closed_hooks.append(self._closed)
        hub.refreshed_hooks.append(self._refreshed)

    @property
    def import_limit(self) -> int:
        return self.settings.library_import_max_mb * MEGABYTE

    async def _opened(self, runtime: UniverseRuntime) -> None:
        self.feed.publish(LibraryStreamKind.UNIVERSE, universe_id=runtime.universe_id)

    async def _closed(self, universe_id: str) -> None:
        self.feed.publish(LibraryStreamKind.UNIVERSE, universe_id=universe_id)

    async def _refreshed(self, record: UniverseRecord) -> None:
        self.feed.publish(LibraryStreamKind.UNIVERSE, universe_id=record.id)

    def changed(self, record: UniverseRecord) -> UniverseRecord:
        self.feed.publish(LibraryStreamKind.UNIVERSE, universe_id=record.id)
        return record

    async def start(self) -> None:
        await self.maintain()
        if self._loop is None:
            self._loop = asyncio.get_running_loop().create_task(self._maintain_forever())

    async def stop(self) -> None:
        if self._loop is not None:
            self._loop.cancel()
            await asyncio.gather(self._loop, return_exceptions=True)
            self._loop = None
        await self.jobs.stop()
        self._checked.clear()

    async def _maintain_forever(self) -> None:
        while True:
            await asyncio.sleep(LIBRARY_MAINTENANCE_SECONDS)
            try:
                await self.maintain()
            except Exception:
                logger.exception("the library upkeep failed")

    async def maintain(self) -> list[str]:
        for job_id in self.jobs.expire():
            self._checked.pop(job_id, None)
        await asyncio.to_thread(self._sweep_leftovers)
        return await self.purge_expired()

    def _sweep_leftovers(self) -> None:
        kept = {path for job in self.jobs.every() for path in (job.file, job.folder) if path is not None}
        for folder in (self.process.imports, self.process.outgoing):
            if not folder.is_dir():
                continue
            for item in folder.iterdir():
                if item not in kept and not any(item.name.startswith(job.id) for job in self.jobs.every() if job.active):
                    remove_quietly(item)

    def busy_reason(self, universe_id: str) -> str | None:
        return self.jobs.busy_reason(universe_id) or self.hub.busy_reason(universe_id)

    def running_jobs(self, universe_id: str) -> list[str]:
        runtime = self.hub.runtime(universe_id)
        kinds = [kind.value for kind in JobKind if runtime.services.jobs.kind_running(kind)] if runtime is not None else []
        library = [job.kind.value for job in self.jobs.of_universe(universe_id) if job.active]
        return sorted({*kinds, *library})

    async def tag_counts(self) -> list[tuple[str, int]]:
        counted: Counter[str] = Counter(tag for record in await self.catalogue.every() for tag in record.tags)
        return sorted(counted.items(), key=lambda item: (item[0].casefold(), item[0]))

    async def recent_events(self, universe_id: str) -> list[LibraryEventRecord]:
        found, _ = await self.catalogue.events(limit=LIBRARY_RECENT_EVENTS, universe_id=universe_id)
        return found

    async def writable(self, universe_id: str) -> UniverseRecord:
        record = await self.catalogue.require(universe_id)
        if record.status is UniverseStatus.ARCHIVED:
            raise ConflictError(ARCHIVED_READ_ONLY)
        return record

    async def create(self, name: str, notes: str, tags: tuple[str, ...], summary: str) -> UniverseRecord:
        return self.changed(await self.hub.create(await self.catalogue.free_name(name), notes=notes, tags=tags, summary=summary))

    async def edit(self, universe_id: str, change: UniverseEdit, status: UniverseStatus | None) -> UniverseRecord:
        record = await self.catalogue.require(universe_id)
        if status is UniverseStatus.ACTIVE and record.status is UniverseStatus.ARCHIVED:
            record = await self.restore(universe_id)
        if change != UniverseEdit():
            await self.writable(universe_id)
            if change.name is not None:
                change = replace(change, name=await self.catalogue.free_name(change.name, keep=universe_id))
            record = self.changed(await self.catalogue.edit(universe_id, change))
        if status is UniverseStatus.ARCHIVED and record.status is UniverseStatus.ACTIVE:
            record = await self.archive(universe_id)
        return record

    async def open(self, universe_id: str) -> UniverseRecord:
        await self.hub.open(universe_id)
        return self.changed(await self.catalogue.require(universe_id))

    async def close(self, universe_id: str) -> UniverseRecord:
        await self.catalogue.require(universe_id)
        await self.hub.close(universe_id)
        return await self.catalogue.require(universe_id)

    async def duplicate(self, universe_id: str, name: str | None) -> UniverseRecord:
        return self.changed(await self.hub.duplicate(universe_id, name))

    def refuse_if_busy(self, universe_id: str, message: str) -> None:
        reason = self.busy_reason(universe_id)
        if reason is not None:
            raise BusyError(message.format(reason=reason))

    async def archive(self, universe_id: str) -> UniverseRecord:
        await self.catalogue.require(universe_id)
        self.refuse_if_busy(universe_id, ARCHIVE_BLOCKED)
        return self.changed(await self.hub.archive(universe_id))

    async def restore(self, universe_id: str) -> UniverseRecord:
        return self.changed(await self.hub.restore(universe_id))

    async def delete(self, universe_id: str) -> TrashEntry:
        record = await self.catalogue.require(universe_id)
        self.refuse_if_busy(universe_id, DELETE_BLOCKED)
        await self.hub.close(universe_id)
        await self.catalogue.remove(universe_id)
        if self.hub.is_open(universe_id):
            await self.hub.close(universe_id, force=True)
        entry_id = await asyncio.to_thread(move_to_trash, self.hub.paths_of(universe_id), self.process.trash, record, datetime.now(UTC))
        await self.catalogue.log(LibraryEventKind.DELETED, universe_id, record.name, entry_id)
        self.feed.publish(LibraryStreamKind.REMOVED, universe_id=universe_id)
        self.feed.publish(LibraryStreamKind.TRASH, universe_id=universe_id)
        return find_entry(self.process.trash, entry_id)

    def purge_at(self, entry: TrashEntry) -> datetime:
        return entry.deleted_at + timedelta(seconds=self.settings.library_trash_days * SECONDS_PER_DAY)

    async def trash(self, offset: int = 0, limit: int = LIBRARY_PAGE_DEFAULT) -> tuple[list[TrashEntry], int, int]:
        found = await asyncio.to_thread(trash_entries, self.process.trash)
        start = max(0, offset)
        return found[start : start + max(1, limit)], len(found), sum(entry.size_bytes for entry in found)

    async def empty_trash(self) -> int:
        found = await asyncio.to_thread(trash_entries, self.process.trash)
        for entry in found:
            await self.purge(entry.entry_id)
        return len(found)

    async def recover(self, entry_id: str) -> UniverseRecord:
        entry = await asyncio.to_thread(find_entry, self.process.trash, entry_id)
        manifest = entry.manifest
        if await self.catalogue.get(manifest.id) is not None or self.hub.paths_of(manifest.id).root.exists():
            manifest = replace(manifest, id=await self.hub.fresh_id())
        manifest = replace(manifest, name=await self.catalogue.free_name(manifest.name))
        await asyncio.to_thread(bring_back, entry, self.hub.paths_of(manifest.id), manifest)
        await self.catalogue.restore_row(manifest)
        if entry.pinned or entry.cover_path:
            await self.catalogue.edit(manifest.id, UniverseEdit(pinned=entry.pinned, cover_path=entry.cover_path))
        record = await self.catalogue.require(manifest.id)
        await self.catalogue.log(LibraryEventKind.RECOVERED, record.id, record.name, entry.entry_id)
        refreshed = await self.hub.refresh(record.id) or record
        self.feed.publish(LibraryStreamKind.TRASH, universe_id=record.id)
        return self.changed(refreshed)

    async def purge(self, entry_id: str) -> None:
        entry = await asyncio.to_thread(find_entry, self.process.trash, entry_id)
        await self._purge_media(entry)
        await asyncio.to_thread(shutil.rmtree, entry.folder, True)
        await self.catalogue.log(LibraryEventKind.PURGED, entry.manifest.id, entry.manifest.name, entry.entry_id)
        self.feed.publish(LibraryStreamKind.TRASH, universe_id=entry.manifest.id)

    async def _purge_media(self, entry: TrashEntry) -> None:
        if self.settings.media_backend is not MediaBackend.S3:
            return
        prefix = entry.manifest.media_prefix
        if any(record.media_prefix == prefix for record in await self.catalogue.every()):
            return
        store = create_media_store(self.settings.for_universe(entry.manifest.id, prefix))
        try:
            await store.ensure_ready()
            for part in COPIED_PREFIXES:
                for info in await list_keys(store, part):
                    await store.delete(info.key)
        finally:
            await store.close()

    async def purge_expired(self) -> list[str]:
        now = datetime.now(UTC)
        purged: list[str] = []
        for entry in await asyncio.to_thread(trash_entries, self.process.trash):
            if self.purge_at(entry) <= now:
                await self.purge(entry.entry_id)
                purged.append(entry.entry_id)
        return purged

    async def export(self, universe_id: str) -> LibraryJob:
        record = await self.catalogue.require(universe_id)
        running = next((job for job in self.jobs.of_universe(universe_id) if job.kind is LibraryJobKind.EXPORT and job.active), None)
        if running is not None:
            return running
        job = self.jobs.begin(LibraryJobKind.EXPORT, LibraryJobStage.SNAPSHOT, record.id, record.name)
        self.jobs.run(job, self._export(job, record))
        return job

    async def _export(self, job: LibraryJob, record: UniverseRecord) -> None:
        try:
            exported = await export_universe(self.hub, record, job, self.jobs, self.process.outgoing)
        except asyncio.CancelledError:
            self.jobs.finish(job, LibraryJobStatus.CANCELLED)
            raise
        except ValidationFailedError as refusal:
            self.jobs.finish(job, LibraryJobStatus.FAILED, refusal.message)
            return
        except Exception:
            logger.exception("the export of universe %s failed", record.id)
            self.jobs.finish(job, LibraryJobStatus.FAILED, UNEXPORTED)
            return
        job.file, job.file_name, job.size_bytes = exported.path, exported.file_name, exported.size
        self.jobs.finish(job, LibraryJobStatus.DONE)

    def export_file(self, job_id: str) -> LibraryJob:
        job = self.jobs.get(job_id, LibraryJobKind.EXPORT)
        if job.status is not LibraryJobStatus.DONE or job.file is None or not job.file.is_file():
            raise NotFoundError(NO_EXPORT_FILE)
        return job

    async def receive(self, chunks: AsyncIterator[bytes], file_name: str) -> LibraryJob:
        folder = self.process.imports / secrets.token_hex(LIBRARY_JOB_ID_BYTES)
        upload = folder / UPLOAD_FILENAME
        await asyncio.to_thread(folder.mkdir, parents=True)
        try:
            size = 0
            with upload.open("wb") as output:
                async for block in chunks:
                    size += len(block)
                    if size > self.import_limit:
                        raise ValidationFailedError(TOO_LARGE.format(limit=self.settings.library_import_max_mb))
                    await asyncio.to_thread(output.write, block)
            if size == 0:
                raise ValidationFailedError(EMPTY_UPLOAD)
        except BaseException:
            await asyncio.to_thread(shutil.rmtree, folder, True)
            raise
        job = self.jobs.begin(LibraryJobKind.IMPORT, LibraryJobStage.CHECK, None, upload_note(file_name))
        job.folder = folder
        job.notes.append(upload_note(file_name))
        self.jobs.run(job, self._check(job, upload))
        return job

    async def _check(self, job: LibraryJob, upload: Path) -> None:
        assert job.folder is not None
        staging = job.folder / LibraryJobStage.CHECK.value
        try:
            await asyncio.to_thread(staging.mkdir)
            checked = await asyncio.to_thread(check_package, upload, staging, self.import_limit * PACKAGE_INFLATE_FACTOR, threadsafe(job, self.jobs))
            await asyncio.to_thread(upload.unlink, True)
        except asyncio.CancelledError:
            self._abandon(job, LibraryJobStatus.CANCELLED)
            raise
        except ValidationFailedError as refusal:
            self._abandon(job, LibraryJobStatus.FAILED, refusal.message)
            return
        except Exception:
            logger.exception("an uploaded universe file could not be checked")
            self._abandon(job, LibraryJobStatus.FAILED, UNCHECKED)
            return
        job.preview = checked.preview()
        job.universe_name = await self.catalogue.free_name(job.preview.name or UNNAMED_IMPORT)
        self._checked[job.id] = checked
        self.jobs.wait(job)

    def _abandon(self, job: LibraryJob, status: LibraryJobStatus, error: str = "") -> None:
        self._checked.pop(job.id, None)
        remove_quietly(job.folder)
        job.folder = None
        self.jobs.finish(job, status, error)

    async def confirm(self, job_id: str, name: str | None) -> LibraryJob:
        job = self.jobs.get(job_id, LibraryJobKind.IMPORT)
        checked = self._checked.get(job.id)
        if job.status is not LibraryJobStatus.WAITING or checked is None:
            raise ConflictError(NOT_WAITING.format(status=spoken(job.status)))
        chosen = await self.catalogue.free_name(name or job.universe_name)
        del self._checked[job.id]
        job.universe_name = chosen
        self.jobs.resume(job, LibraryJobStage.PLACE)
        self.jobs.run(job, self._place(job, checked, chosen))
        return job

    async def _place(self, job: LibraryJob, checked: CheckedPackage, name: str) -> None:
        note = job.notes[0] if job.notes else ""
        try:
            record = await place_package(self.hub, checked, job, self.jobs, name=name, origin_note=note)
        except asyncio.CancelledError:
            self._abandon(job, LibraryJobStatus.CANCELLED)
            raise
        except ValidationFailedError as refusal:
            self._abandon(job, LibraryJobStatus.FAILED, refusal.message)
            return
        except Exception:
            logger.exception("an imported universe could not be placed")
            self._abandon(job, LibraryJobStatus.FAILED, UNPLACED)
            return
        job.universe_id, job.universe_name = record.id, record.name
        remove_quietly(job.folder)
        job.folder = None
        self.jobs.finish(job, LibraryJobStatus.DONE)
        self.changed(record)

    async def cancel(self, job_id: str, kind: LibraryJobKind) -> LibraryJob:
        job = self.jobs.get(job_id, kind)
        task = job.task
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self._checked.pop(job.id, None)
        if job.status in (LibraryJobStatus.RUNNING, LibraryJobStatus.WAITING):
            remove_quietly(job.file)
            remove_quietly(job.folder)
            job.file, job.folder = None, None
            self.jobs.finish(job, LibraryJobStatus.CANCELLED)
            return job
        self.jobs.forget(job)
        self.jobs.announce(job)
        return job

    async def set_cover(self, universe_id: str, data: bytes) -> UniverseRecord:
        record = await self.writable(universe_id)
        mime = mime_of(data)
        if mime is None:
            raise ValidationFailedError(NOT_AN_IMAGE)
        root = self.hub.paths_of(universe_id).root
        name = f"{COVER_STEM}{EXTENSIONS[mime]}"

        def write() -> None:
            root.mkdir(parents=True, exist_ok=True)
            (root / name).write_bytes(data)
            if record.cover_path and record.cover_path != name:
                (root / record.cover_path).unlink(missing_ok=True)

        await asyncio.to_thread(write)
        return self.changed(await self.catalogue.edit(universe_id, UniverseEdit(cover_path=name)))

    async def paint_prompt(self, universe_id: str) -> str:
        record = await self.writable(universe_id)
        runtime = await self.hub.acquire(universe_id)
        try:
            async with runtime.services.database.read() as session:
                cosmos = await CosmosRepository(session).get()
        finally:
            self.hub.release(runtime)
        seed = " ".join(cosmos.seed_idea.split()) if cosmos is not None else ""
        return (seed or record.summary or record.name)[:COVER_PROMPT_MAX_LENGTH]

    async def paint_cover(self, universe_id: str, prompt: str) -> bytes:
        await self.writable(universe_id)
        runtime = await self.hub.acquire(universe_id)
        try:
            return await runtime.services.application.images.paint(prompt)
        finally:
            self.hub.release(runtime)

    async def cover_from_media(self, universe_id: str, file_name: str) -> UniverseRecord:
        record = await self.writable(universe_id)
        key = original_key(file_name) if file_name and "/" not in file_name else ""
        if not is_original_key(key):
            raise NotFoundError(NO_SUCH_IMAGE)
        async with media_of(self.hub, record) as store:
            data = await read_all(store, key)
        if data is None:
            raise NotFoundError(NO_SUCH_IMAGE)
        return await self.set_cover(universe_id, data)

    async def clear_cover(self, universe_id: str) -> UniverseRecord:
        record = await self.writable(universe_id)
        if record.cover_path:
            await asyncio.to_thread((self.hub.paths_of(universe_id).root / record.cover_path).unlink, True)
        return self.changed(await self.catalogue.edit(universe_id, UniverseEdit(clear_cover=True)))

    async def cover_file(self, universe_id: str) -> Path:
        record = await self.catalogue.require(universe_id)
        root = self.hub.paths_of(universe_id).root.resolve()
        found = (root / record.cover_path).resolve() if record.cover_path else None
        if found is None or not found.is_relative_to(root) or not found.is_file():
            raise NotFoundError(NO_COVER)
        return found
