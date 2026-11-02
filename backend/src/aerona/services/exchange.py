import asyncio
import inspect
import io
import re
import secrets
import shutil
import sqlite3
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from aerona.constants.maintenance import (
    CORE_TABLES,
    IMPORT_SAFETY_LABEL,
    MERGE_CONFIRMATION,
    PACKAGE_MAX_BYTES,
    PACKAGE_NAME_MAX_LENGTH,
    PACKAGE_READ_BYTES,
    PACKAGE_SUFFIX,
    REPLACE_CONFIRMATION,
    WORK_DIRNAME,
)
from aerona.core.errors import ValidationFailedError
from aerona.events.bus import EventBus
from aerona.events.change_feed import ChangeFeed
from aerona.events.kinds import EventKind
from aerona.media.bridge import blocking_call, blocking_opener
from aerona.media.keys import is_original_key, is_sha256
from aerona.media.store import MediaStore
from aerona.services.backups import BackupService, is_safe_image_name, referenced_objects, vacuum_into
from aerona.services.discovery import DiscoveryService, GuestWorld
from aerona.services.images.transfer import MediaReceiver, known_objects, relink_images
from aerona.services.world_merge import MergeSummary, WorldMerger
from aerona.services.world_package import PackagedObject, PackageManifest, read_package, write_package
from aerona.settings import Settings

NAME_RUNS = re.compile(r"[^\w]+")
META_QUERY = "SELECT name, epoch FROM cosmos LIMIT 1"
CREATOR_QUERY = "SELECT name FROM nodes WHERE kind = 'creator' LIMIT 1"
VIRTUAL_QUERY = "SELECT name FROM sqlite_master WHERE type = 'table' AND sql LIKE 'CREATE VIRTUAL TABLE%'"
OBJECT_QUERY = "SELECT type, name FROM sqlite_master WHERE type IN ('trigger', 'view')"
UNSAFE_IMAGE_QUERY = "SELECT id, file_name, object_key, sha256 FROM images"
EXPORT_OBJECTS_QUERY = "SELECT object_key, MIN(sha256) FROM images GROUP BY object_key ORDER BY object_key"
DEFAULT_WORLD_NAME = "world"
CORRUPT_PACKAGE = "The database in the file is corrupt or not a Weavers of the Void world."
MERGED_MESSAGE = "{name} merged into your world. The previous world was saved as {backup}."
IMPORTED_MESSAGE = "{name} imported. The previous world was saved as {backup}."
DISCOVERY_MESSAGE = "Discovery mode: {name} (Epoch {epoch}) opened read-only. Your own world is waiting aside."
DISCOVERY_ENDED = "Discovery ended; {name} closed and your own world is back."
GUEST_FALLBACK = "the guest world"

WorldChangeCallback = Callable[[], Awaitable[None] | None]


class ImportMode(StrEnum):
    REPLACE = "replace"
    MERGE = "merge"
    DISCOVERY = "discovery"


@dataclass(frozen=True)
class PackageMeta:
    name: str
    epoch: int | None
    creator: str | None
    date: str


@dataclass(frozen=True)
class ExportedPackage:
    file_name: str
    path: Path
    size: int


@dataclass(frozen=True)
class ImportResult:
    mode: ImportMode
    world: PackageMeta
    safety_backup: str | None
    merge: MergeSummary | None = None


def package_file_name(name: str, epoch: int | None) -> str:
    base = NAME_RUNS.sub("-", name).strip("-")[:PACKAGE_NAME_MAX_LENGTH] or DEFAULT_WORLD_NAME
    return f"{base}-epoch{epoch or 0}{PACKAGE_SUFFIX}"


def read_meta(path: Path) -> PackageMeta:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        row = connection.execute(META_QUERY).fetchone()
        creator = connection.execute(CREATOR_QUERY).fetchone()
    except sqlite3.Error:
        row, creator = None, None
    finally:
        connection.close()
    return PackageMeta(
        name=str(row[0]) if row else DEFAULT_WORLD_NAME,
        epoch=int(row[1]) if row else None,
        creator=str(creator[0]) if creator else None,
        date=datetime.now(UTC).isoformat(),
    )


def image_objects(path: Path) -> list[tuple[str, str]]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = connection.execute(EXPORT_OBJECTS_QUERY).fetchall()
    except sqlite3.Error:
        return []
    finally:
        connection.close()
    return [(str(key), str(digest)) for key, digest in rows if is_original_key(str(key)) and is_sha256(str(digest))]


def image_row_safe(file_name: object, object_key: object, digest: object) -> bool:
    return is_safe_image_name(str(file_name)) and is_original_key(str(object_key)) and is_sha256(str(digest))


def sanitize_database(path: Path) -> None:
    try:
        connection = sqlite3.connect(path)
    except sqlite3.Error as error:
        raise ValidationFailedError(CORRUPT_PACKAGE) from error
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("PRAGMA trusted_schema = OFF")
        check = connection.execute("PRAGMA quick_check").fetchone()
        if check is None or check[0] != "ok":
            raise ValidationFailedError(CORRUPT_PACKAGE)
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if not set(CORE_TABLES) <= tables or connection.execute(META_QUERY).fetchone() is None:
            raise ValidationFailedError(CORRUPT_PACKAGE)
        if connection.execute(VIRTUAL_QUERY).fetchone() is not None:
            raise ValidationFailedError(CORRUPT_PACKAGE)
        for kind, name in connection.execute(OBJECT_QUERY).fetchall():
            connection.execute(f'DROP {"TRIGGER" if kind == "trigger" else "VIEW"} IF EXISTS "{name}"')
        if "images" in tables:
            unsafe = [row[0] for row in connection.execute(UNSAFE_IMAGE_QUERY).fetchall() if not image_row_safe(row[1], row[2], row[3])]
            connection.executemany("DELETE FROM images WHERE id = ?", [(item,) for item in unsafe])
        connection.commit()
    except sqlite3.Error as error:
        raise ValidationFailedError(CORRUPT_PACKAGE) from error
    finally:
        connection.close()


class WorldChangedHook:
    def __init__(self, feed: ChangeFeed, bus: EventBus | None = None) -> None:
        self._feed = feed
        self._bus = bus
        self._callbacks: list[WorldChangeCallback] = []

    def register(self, callback: WorldChangeCallback) -> None:
        self._callbacks.append(callback)

    async def fire(self, message: str) -> None:
        for callback in self._callbacks:
            result = callback()
            if inspect.isawaitable(result):
                await result
        self._feed.reset()
        if self._bus is not None:
            self._bus.publish(EventKind.WORLD_REPLACED, {"message": message, "version": self._feed.version})
            self._bus.publish(EventKind.SYSTEM_NOTE, {"text": message})


class ExchangeService:
    def __init__(
        self, settings: Settings, backups: BackupService, discovery: DiscoveryService, hook: WorldChangedHook, merger: WorldMerger, *, store: MediaStore
    ) -> None:
        self._merger = merger
        self._settings = settings
        self._backups = backups
        self._discovery = discovery
        self._hook = hook
        self._store = store

    @property
    def work_dir(self) -> Path:
        return self._settings.data_dir / WORK_DIRNAME

    def _temporary(self, prefix: str, suffix: str) -> Path:
        self.work_dir.mkdir(parents=True, exist_ok=True)
        return self.work_dir / f"{prefix}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3)}{suffix}"

    async def export(self, *, images: bool = True, backup_name: str | None = None) -> ExportedPackage:
        source = self._backups.path_of(backup_name) if backup_name else None
        copy = self._temporary("export", ".db")
        try:
            if source is None:
                await asyncio.to_thread(vacuum_into, self._settings.database_path, copy)
            else:
                await asyncio.to_thread(shutil.copy2, source, copy)
            meta = await asyncio.to_thread(read_meta, copy)
            objects = await self._packaged_objects(copy) if images else ()
            manifest = PackageManifest(name=meta.name, epoch=meta.epoch, creator=meta.creator, date=meta.date, objects=objects)
            target = self._temporary("export", PACKAGE_SUFFIX)
            opener = blocking_opener(self._store, asyncio.get_running_loop())
            try:
                await asyncio.to_thread(write_package, target, manifest, copy, opener)
            except BaseException:
                await asyncio.to_thread(target.unlink, True)
                raise
            size = (await asyncio.to_thread(target.stat)).st_size
            return ExportedPackage(file_name=package_file_name(meta.name, meta.epoch), path=target, size=size)
        finally:
            await asyncio.to_thread(copy.unlink, True)

    async def _packaged_objects(self, database: Path) -> tuple[PackagedObject, ...]:
        found: list[PackagedObject] = []
        for key, digest in await asyncio.to_thread(image_objects, database):
            info = await self._store.head(key)
            if info is not None:
                found.append(PackagedObject(key=key, sha256=digest, size=info.size))
        return tuple(found)

    async def import_package(self, data: bytes, mode: ImportMode, confirmation: str | None = None) -> ImportResult:
        self._discovery.ensure_not_active()
        if not data:
            raise ValidationFailedError("The file is empty.")
        if len(data) > PACKAGE_MAX_BYTES:
            raise ValidationFailedError("The file is too large.")
        if mode is ImportMode.REPLACE and confirmation != REPLACE_CONFIRMATION:
            raise ValidationFailedError(f"Type {REPLACE_CONFIRMATION} to replace your world.")
        if mode is ImportMode.MERGE and confirmation != MERGE_CONFIRMATION:
            raise ValidationFailedError(f"Type {MERGE_CONFIRMATION} to merge the file into your world.")
        database = self._temporary("import", ".db")
        receiver = MediaReceiver(self._store, await asyncio.to_thread(known_objects, self._settings.database_path))
        try:
            manifest = await self._unpack(data, database, receiver)
            meta = await asyncio.to_thread(read_meta, database)
            if mode is ImportMode.MERGE:
                safety = await self._backups.take(IMPORT_SAFETY_LABEL)
                summary = await self._merger.merge(database)
                await self._hook.fire(MERGED_MESSAGE.format(name=meta.name, backup=safety.file))
                return ImportResult(mode=mode, world=meta, safety_backup=safety.file, merge=summary)
            if mode is ImportMode.DISCOVERY:
                guest = GuestWorld(meta.name, meta.epoch, meta.creator, manifest.date or meta.date)
                await self._discovery.open(database, guest, list(receiver.written))
                await self._hook.fire(DISCOVERY_MESSAGE.format(name=meta.name, epoch=meta.epoch or 0))
                return ImportResult(mode=mode, world=meta, safety_backup=None)
            safety = await self._backups.take(IMPORT_SAFETY_LABEL)
            await self._backups.load_file(database)
            await self._hook.fire(IMPORTED_MESSAGE.format(name=meta.name, backup=safety.file))
            return ImportResult(mode=mode, world=meta, safety_backup=safety.file)
        except BaseException:
            await receiver.discard()
            raise
        finally:
            await asyncio.to_thread(database.unlink, True)

    async def _unpack(self, data: bytes, database: Path, receiver: MediaReceiver) -> PackageManifest:
        sink = blocking_call(asyncio.get_running_loop(), receiver.receive)
        manifest = await asyncio.to_thread(read_package, io.BytesIO(data), database, sink)
        await asyncio.to_thread(sanitize_database, database)
        await receiver.adopt_present(await asyncio.to_thread(referenced_objects, database))
        await asyncio.to_thread(relink_images, database, receiver.mapping, receiver.digests)
        return manifest

    async def end_discovery(self) -> GuestWorld | None:
        state = self._discovery.state()
        guest = await self._discovery.end()
        if state is not None:
            await self._backups.collector.collect(state.images)
        await self._hook.fire(DISCOVERY_ENDED.format(name=guest.name if guest else GUEST_FALLBACK))
        return guest


async def stream_and_delete(path: Path) -> AsyncIterator[bytes]:
    try:
        with path.open("rb") as handle:
            while chunk := await asyncio.to_thread(handle.read, PACKAGE_READ_BYTES):
                yield chunk
    finally:
        await asyncio.to_thread(path.unlink, True)
