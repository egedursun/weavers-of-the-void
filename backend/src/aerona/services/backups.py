import asyncio
import json
import re
import secrets
import shutil
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aerona.constants.maintenance import (
    BACKUP_LABEL_MAX_LENGTH,
    BACKUP_MANIFEST_SUFFIX,
    BACKUP_PREFIX,
    BACKUP_RANDOM_LENGTH,
    BACKUP_SUFFIX,
    BACKUP_TIMESTAMP_FORMAT,
    CORE_TABLES,
    EPOCH_LABEL_PREFIX,
    MANUAL_LABEL,
    RASTER_EXTENSIONS,
    RESET_CONFIRMATION,
    RESET_SAFETY_LABEL,
    RESTORE_CONFIRMATION,
    RESTORE_SAFETY_LABEL,
    SAFE_FILE_NAME_PATTERN,
    SAFE_IMAGE_NAME_MAX_LENGTH,
    SECONDARY_TARGET_FILENAME,
    SECONDARY_TARGET_KEY,
)
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.migrations import upgrade_to_head
from aerona.db.session import Database
from aerona.events.bus import EventBus
from aerona.events.kinds import EventKind
from aerona.media.keys import is_original_key
from aerona.media.store import MediaStore
from aerona.rules.registry import Rules
from aerona.services.images.collection import MediaCollector
from aerona.services.world import reset_world
from aerona.settings import Settings

LABEL_PATTERN = re.compile(rf"^{BACKUP_PREFIX}-(.+?)-\d{{4}}-\d{{2}}-\d{{2}}T")
EPOCH_LABEL = re.compile(rf"^{EPOCH_LABEL_PREFIX}(\d+)$")
UNSAFE_LABEL = re.compile(r"[^\w-]")
UNSAFE_NAME = re.compile(r"[^\w.\-]")
SAFE_FILE_NAME = re.compile(SAFE_FILE_NAME_PATTERN)
RANDOM_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"
MILLISECONDS_DIGITS = 3
QUICK_CHECK_OK = "ok"
WAL_SUFFIXES = ("-wal", "-shm")
OBJECT_QUERY = "SELECT DISTINCT object_key FROM images"
TABLE_QUERY = "SELECT name FROM sqlite_master WHERE type = 'table'"
EPOCH_QUERY = "SELECT epoch FROM cosmos LIMIT 1"
MIGRATION_TABLE = "alembic_version"
MANIFEST_OBJECTS = "objects"


@dataclass(frozen=True)
class BackupInfo:
    file: str
    size: int
    modified: datetime
    label: str


@dataclass(frozen=True)
class RestoreResult:
    restored: str
    safety: str


def sanitize_label(label: str | None) -> str:
    cleaned = UNSAFE_LABEL.sub("", label or "")[:BACKUP_LABEL_MAX_LENGTH]
    return cleaned or MANUAL_LABEL


def sanitize_file_name(name: str) -> str:
    return UNSAFE_NAME.sub("", name)


def label_of(file_name: str) -> str:
    match = LABEL_PATTERN.match(file_name)
    return match.group(1) if match else MANUAL_LABEL


def backup_file_name(label: str, now: datetime) -> str:
    stamp = now.strftime(BACKUP_TIMESTAMP_FORMAT) + f"-{now.microsecond // 1000:0{MILLISECONDS_DIGITS}d}"
    suffix = "".join(secrets.choice(RANDOM_ALPHABET) for _ in range(BACKUP_RANDOM_LENGTH))
    return f"{BACKUP_PREFIX}-{sanitize_label(label)}-{stamp}-{suffix}{BACKUP_SUFFIX}"


def is_safe_file_name(name: str) -> bool:
    return bool(SAFE_FILE_NAME.match(name))


def is_safe_image_name(name: str) -> bool:
    return len(name) <= SAFE_IMAGE_NAME_MAX_LENGTH and is_safe_file_name(name) and Path(name).suffix.lower() in RASTER_EXTENSIONS


def _read_only(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def referenced_objects(path: Path) -> set[str]:
    connection = _read_only(path)
    try:
        tables = {row[0] for row in connection.execute(TABLE_QUERY)}
        if "images" not in tables:
            return set()
        return {str(row[0]) for row in connection.execute(OBJECT_QUERY) if row[0] and is_original_key(str(row[0]))}
    finally:
        connection.close()


def validate_database(path: Path) -> None:
    try:
        connection = _read_only(path)
    except sqlite3.Error as error:
        raise ValidationFailedError("Could not open the backup file.") from error
    try:
        try:
            check = connection.execute("PRAGMA quick_check").fetchone()
        except sqlite3.Error as error:
            raise ValidationFailedError("The backup file is corrupt.") from error
        if check is None or check[0] != QUICK_CHECK_OK:
            raise ValidationFailedError("The backup file is corrupt.")
        tables = {row[0] for row in connection.execute(TABLE_QUERY)}
        if not set(CORE_TABLES) <= tables:
            raise ValidationFailedError("This file is not a Weavers of the Void world.")
    finally:
        connection.close()


def vacuum_into(source: Path, target: Path) -> None:
    connection = sqlite3.connect(source)
    try:
        connection.execute("VACUUM INTO ?", (str(target),))
    finally:
        connection.close()


def database_epoch(path: Path) -> int | None:
    connection = _read_only(path)
    try:
        row = connection.execute(EPOCH_QUERY).fetchone()
        return int(row[0]) if row else None
    except sqlite3.Error:
        return None
    finally:
        connection.close()


def has_migration_table(path: Path) -> bool:
    connection = _read_only(path)
    try:
        return MIGRATION_TABLE in {row[0] for row in connection.execute(TABLE_QUERY)}
    finally:
        connection.close()


def no_pins() -> set[str]:
    return set()


class BackupService:
    def __init__(
        self,
        settings: Settings,
        database: Database,
        rules: Callable[[], Rules],
        bus: EventBus | None = None,
        *,
        store: MediaStore,
        pinned: Callable[[], set[str]] = no_pins,
    ) -> None:
        self._settings = settings
        self._database = database
        self._rules = rules
        self._bus = bus
        self._pinned = pinned
        self.collector = MediaCollector(store, self.referenced_objects)

    @property
    def directory(self) -> Path:
        return self._settings.backups_dir

    @property
    def live_path(self) -> Path:
        return self._settings.database_path

    def path_of(self, name: str) -> Path:
        cleaned = sanitize_file_name(name)
        path = self.directory / cleaned
        if not cleaned or not path.is_file():
            raise NotFoundError("No such backup.")
        return path

    async def take(self, label: str = MANUAL_LABEL) -> BackupInfo:
        info, deleted = await asyncio.to_thread(self._take, label)
        if deleted:
            await self.collector.sweep()
        if self._bus is not None:
            self._bus.publish(EventKind.BACKUP_TAKEN, {"file": info.file, "label": sanitize_label(label)})
        return info

    def _take(self, label: str) -> tuple[BackupInfo, int]:
        self.directory.mkdir(parents=True, exist_ok=True)
        name = backup_file_name(label, datetime.now())
        target = self.directory / name
        vacuum_into(self.live_path, target)
        self._write_manifest(target, label)
        self._copy_secondary(target)
        deleted = self._rotate(self._rules())
        return self._info(target), deleted

    def _write_manifest(self, target: Path, label: str) -> None:
        manifest = {
            "label": sanitize_label(label),
            "epoch": database_epoch(target),
            "created": datetime.now(UTC).isoformat(),
            "size": target.stat().st_size,
            "objects": sorted(referenced_objects(target)),
        }
        target.with_suffix(BACKUP_MANIFEST_SUFFIX).write_text(json.dumps(manifest), encoding="utf-8")

    @property
    def _secondary_file(self) -> Path:
        return self._settings.data_dir / SECONDARY_TARGET_FILENAME

    def secondary_target(self) -> Path | None:
        stored = self._secondary_file
        if stored.is_file():
            value = json.loads(stored.read_text(encoding="utf-8")).get(SECONDARY_TARGET_KEY)
            return Path(value) if value else None
        return self._settings.secondary_backup_dir

    def set_secondary_target(self, directory: str | None) -> Path | None:
        cleaned = (directory or "").strip()
        target = Path(cleaned).expanduser() if cleaned else None
        if target is not None:
            if not target.is_absolute():
                raise ValidationFailedError("The secondary backup folder must be an absolute path.")
            if target.resolve() == self.directory.resolve():
                raise ValidationFailedError("The secondary backup folder must differ from the main backup folder.")
            target.mkdir(parents=True, exist_ok=True)
        self._secondary_file.parent.mkdir(parents=True, exist_ok=True)
        self._secondary_file.write_text(json.dumps({SECONDARY_TARGET_KEY: str(target) if target is not None else None}), encoding="utf-8")
        return target

    def _copy_secondary(self, target: Path) -> None:
        secondary = self.secondary_target()
        if secondary is None:
            return
        secondary.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, secondary / target.name)
        keep = self._rules().backup.secondary_target_backups
        files = sorted(secondary.glob(f"{BACKUP_PREFIX}-*{BACKUP_SUFFIX}"), key=lambda item: item.stat().st_mtime, reverse=True)
        for stale in files[keep:]:
            stale.unlink(missing_ok=True)

    def backups(self) -> list[BackupInfo]:
        if not self.directory.is_dir():
            return []
        files = [path for path in self.directory.glob(f"*{BACKUP_SUFFIX}") if path.is_file()]
        return sorted((self._info(path) for path in files), key=lambda info: info.modified, reverse=True)

    def _info(self, path: Path) -> BackupInfo:
        stat = path.stat()
        return BackupInfo(file=path.name, size=stat.st_size, modified=datetime.fromtimestamp(stat.st_mtime, UTC), label=label_of(path.name))

    def _rotate(self, rules: Rules) -> int:
        policy = rules.backup
        epoch_seen = 0
        counts: dict[str, int] = {}
        deleted = 0
        for info in self.backups():
            match = EPOCH_LABEL.match(info.label)
            if match:
                epoch_seen += 1
                if epoch_seen > policy.recent_epoch_backups and int(match.group(1)) % policy.milestone_epoch_multiple != 0:
                    deleted += self._delete(info.file)
                continue
            counts[info.label] = counts.get(info.label, 0) + 1
            limit = policy.manual_backups if info.label == MANUAL_LABEL else policy.safety_backups_per_kind
            if counts[info.label] > limit:
                deleted += self._delete(info.file)
        return deleted

    def _delete(self, name: str) -> int:
        path = self.directory / name
        path.unlink(missing_ok=True)
        path.with_suffix(BACKUP_MANIFEST_SUFFIX).unlink(missing_ok=True)
        return 1

    async def prune_media(self) -> int:
        return await self.collector.sweep()

    def referenced_objects(self) -> set[str] | None:
        try:
            used = referenced_objects(self.live_path) if self.live_path.is_file() else set()
            for info in self.backups():
                path = self.directory / info.file
                manifest = path.with_suffix(BACKUP_MANIFEST_SUFFIX)
                if manifest.is_file():
                    listed = json.loads(manifest.read_text(encoding="utf-8"))[MANIFEST_OBJECTS]
                    used |= {str(key) for key in listed}
                else:
                    used |= referenced_objects(path)
            return used | self._pinned()
        except (sqlite3.Error, OSError, ValueError, KeyError, TypeError):
            return None

    async def validate(self, name: str) -> None:
        await asyncio.to_thread(validate_database, self.path_of(name))

    async def restore(self, name: str, confirmation: str) -> RestoreResult:
        if confirmation != RESTORE_CONFIRMATION:
            raise ValidationFailedError(f"Type {RESTORE_CONFIRMATION} to restore a backup.")
        cleaned = sanitize_file_name(name)
        if not cleaned.endswith(BACKUP_SUFFIX):
            raise ValidationFailedError("Only .db backups can be restored.")
        path = self.path_of(cleaned)
        await asyncio.to_thread(validate_database, path)
        safety = await self.take(RESTORE_SAFETY_LABEL)
        await self.load_file(path)
        return RestoreResult(restored=cleaned, safety=safety.file)

    async def load_file(self, source: Path) -> None:
        await self._database.dispose()
        staged = self.live_path.with_name(self.live_path.name + ".incoming")
        await asyncio.to_thread(shutil.copy2, source, staged)
        for suffix in WAL_SUFFIXES:
            self.live_path.with_name(self.live_path.name + suffix).unlink(missing_ok=True)
        staged.replace(self.live_path)
        if await asyncio.to_thread(has_migration_table, self.live_path):
            await upgrade_to_head(self._settings.database_url)

    def latest(self) -> BackupInfo | None:
        found = self.backups()
        return found[0] if found else None

    async def reset(self, confirmation: str) -> str:
        if confirmation != RESET_CONFIRMATION:
            raise ValidationFailedError(f"Type {RESET_CONFIRMATION} to reset the world.")
        safety = await self.take(RESET_SAFETY_LABEL)
        async with self._database.write() as session:
            await reset_world(session)
        return safety.file
