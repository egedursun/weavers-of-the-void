import asyncio
import hashlib
import os
import shutil
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aerona.constants.app import APP_VERSION
from aerona.constants.library_packages import PARTIAL_SUFFIX
from aerona.constants.maintenance import PACKAGE_MEDIA_MEMBER_PREFIX, PACKAGE_SUFFIX
from aerona.core.errors import ValidationFailedError
from aerona.domain.enums.library import LibraryEventKind, UniverseOrigin
from aerona.domain.enums.library_jobs import LibraryJobStage
from aerona.media.factory import create_media_store
from aerona.media.keys import is_original_key
from aerona.media.store import MediaStore, list_keys, read_all
from aerona.paths import UniversePaths
from aerona.services.backups import referenced_objects
from aerona.services.exchange import package_file_name, read_meta
from aerona.services.images.transfer import relink_images
from aerona.services.library.catalogue import NewUniverse, UniverseRecord
from aerona.services.library.hub import UniverseHub, copy_database
from aerona.services.library.jobs import LibraryJob, LibraryJobs
from aerona.services.library.package import (
    PACKED_PREFIXES,
    CheckedPackage,
    LibraryManifest,
    PackedFile,
    database_file,
    media_member,
    packable_key,
    staged_path,
    write_library_package,
)
from aerona.services.world_package import PackagedObject, PackageManifest

NO_DATABASE = "This universe has no database to export."
STAGING_SUFFIX = ".staging"

Progress = Callable[[int, int], None]


@dataclass(frozen=True)
class ExportedFile:
    path: Path
    file_name: str
    size: int


def threadsafe(job: LibraryJob, jobs: LibraryJobs) -> Progress:
    loop = asyncio.get_running_loop()

    def report(done: int, total: int) -> None:
        loop.call_soon_threadsafe(jobs.advance, job, done, total)

    return report


@asynccontextmanager
async def media_of(hub: UniverseHub, record: UniverseRecord) -> AsyncIterator[MediaStore]:
    running = hub.runtime(record.id)
    if running is not None:
        yield running.services.application.media
        return
    store = create_media_store(hub.settings_of(record))
    await store.ensure_ready()
    try:
        yield store
    finally:
        await store.close()


def stage_object(staging: Path, key: str, data: bytes) -> PackedFile:
    member = media_member(key)
    target = staged_path(staging, member)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return PackedFile(path=member, size=len(data), sha256=hashlib.sha256(data).hexdigest())


async def gather_media(store: MediaStore, staging: Path, job: LibraryJob, jobs: LibraryJobs) -> list[PackedFile]:
    keys = sorted({info.key for prefix in PACKED_PREFIXES for info in await list_keys(store, prefix) if packable_key(info.key)})
    jobs.enter(job, LibraryJobStage.GATHER, len(keys))
    gathered: list[PackedFile] = []
    for index, key in enumerate(keys, 1):
        data = await read_all(store, key)
        if data is not None:
            gathered.append(await asyncio.to_thread(stage_object, staging, key, data))
        jobs.advance(job, index, len(keys))
    return gathered


def legacy_objects(media: list[PackedFile], referenced: set[str]) -> tuple[PackagedObject, ...]:
    found: list[PackagedObject] = []
    for item in media:
        key = item.path.removeprefix(PACKAGE_MEDIA_MEMBER_PREFIX)
        if is_original_key(key) and key in referenced:
            found.append(PackagedObject(key=key, sha256=item.sha256, size=item.size))
    return tuple(found)


async def export_universe(hub: UniverseHub, record: UniverseRecord, job: LibraryJob, jobs: LibraryJobs, outgoing: Path) -> ExportedFile:
    source = hub.paths_of(record.id)
    if not source.database.is_file():
        raise ValidationFailedError(NO_DATABASE)
    await asyncio.to_thread(outgoing.mkdir, parents=True, exist_ok=True)
    staging = UniversePaths(outgoing / f"{job.id}{STAGING_SUFFIX}")
    target = outgoing / f"{job.id}{PACKAGE_SUFFIX}"
    partial = target.with_name(f"{target.name}{PARTIAL_SUFFIX}")
    try:
        jobs.enter(job, LibraryJobStage.SNAPSHOT)
        await asyncio.to_thread(copy_database, source, staging)
        fresh = await hub.refresh(record.id) or record
        database = await asyncio.to_thread(database_file, staging.database)
        meta = await asyncio.to_thread(read_meta, staging.database)
        async with media_of(hub, record) as store:
            media = await gather_media(store, staging.root, job, jobs)
        referenced = await asyncio.to_thread(referenced_objects, staging.database)
        exported_at = datetime.now(UTC)
        legacy = PackageManifest(
            name=meta.name, epoch=meta.epoch, creator=meta.creator, date=exported_at.isoformat(), objects=legacy_objects(media, referenced)
        )
        manifest = LibraryManifest(
            universe_id=fresh.id,
            name=fresh.name,
            summary=fresh.summary,
            notes=fresh.notes,
            tags=fresh.tags,
            created_at=fresh.created_at,
            exported_at=exported_at,
            app_version=APP_VERSION,
            schema_revision=fresh.schema_revision,
            epoch=fresh.epoch,
            year=fresh.year,
            population=fresh.population,
            sons=fresh.sons,
            files=(database, *media),
        )
        jobs.enter(job, LibraryJobStage.PACK, sum(item.size for item in manifest.files))
        await asyncio.to_thread(write_library_package, partial, legacy, manifest, staging.root, threadsafe(job, jobs))
        await asyncio.to_thread(os.replace, partial, target)
        size = (await asyncio.to_thread(target.stat)).st_size
        file_name = package_file_name(fresh.name, fresh.epoch)
        await hub.catalogue.log(LibraryEventKind.EXPORTED, fresh.id, fresh.name, file_name)
        return ExportedFile(path=target, file_name=file_name, size=size)
    except BaseException:
        await asyncio.to_thread(partial.unlink, True)
        await asyncio.to_thread(target.unlink, True)
        raise
    finally:
        await asyncio.to_thread(shutil.rmtree, staging.root, True)


async def forget_media(store: MediaStore, keys: list[str]) -> None:
    for key in keys:
        await store.delete(key)


async def place_package(hub: UniverseHub, checked: CheckedPackage, job: LibraryJob, jobs: LibraryJobs, *, name: str, origin_note: str) -> UniverseRecord:
    universe_id = await hub.fresh_id()
    paths = hub.paths_of(universe_id)
    prefix = hub.media_prefix_of(universe_id)
    store = create_media_store(hub.settings.for_universe(universe_id, prefix))
    written: list[str] = []
    preview = checked.preview()
    try:
        paths.root.mkdir(parents=True)
        await asyncio.to_thread(os.replace, checked.database, paths.database)
        await store.ensure_ready()
        media = checked.media()
        jobs.enter(job, LibraryJobStage.PLACE, len(media))
        for index, item in enumerate(media, 1):
            key = item.path.removeprefix(PACKAGE_MEDIA_MEMBER_PREFIX)
            await store.put(key, await asyncio.to_thread(staged_path(checked.staging, item.path).read_bytes))
            written.append(key)
            jobs.advance(job, index, len(media))
        if checked.library is None:
            placed = {key: key for key in written if is_original_key(key)}
            digests = {item.path.removeprefix(PACKAGE_MEDIA_MEMBER_PREFIX): item.sha256 for item in media}
            await asyncio.to_thread(relink_images, paths.database, placed, digests)
        jobs.enter(job, LibraryJobStage.REGISTER)
        new = NewUniverse(
            name=name,
            origin=UniverseOrigin.IMPORTED,
            media_prefix=prefix,
            app_version=APP_VERSION,
            notes=preview.notes,
            summary=preview.summary,
            origin_note=origin_note,
            tags=preview.tags,
        )
        return await hub.register(universe_id, new, LibraryEventKind.IMPORTED, origin_note)
    except BaseException:
        await forget_media(store, written)
        await asyncio.to_thread(shutil.rmtree, paths.root, True)
        if await hub.catalogue.get(universe_id) is not None:
            await hub.catalogue.remove(universe_id)
        raise
    finally:
        await store.close()
