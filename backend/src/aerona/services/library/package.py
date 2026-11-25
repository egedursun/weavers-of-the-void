import hashlib
import io
import json
import sqlite3
import tarfile
import zlib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import IO, Any, Final

from alembic.script import ScriptDirectory
from alembic.util import CommandError

from aerona.constants.library_packages import (
    HASH_CHUNK_BYTES,
    LIBRARY_PACKAGE_FORMAT,
    LIBRARY_PACKAGE_MEMBER,
    LIBRARY_PACKAGE_VERSION,
    STAGED_MEDIA_DIRNAME,
)
from aerona.constants.maintenance import (
    PACKAGE_DATABASE_MEMBER,
    PACKAGE_MANIFEST_MAX_BYTES,
    PACKAGE_MANIFEST_MEMBER,
    PACKAGE_MEDIA_MEMBER_PREFIX,
    PACKAGE_OBJECT_MAX_BYTES,
)
from aerona.constants.media import ORIGINALS_PREFIX
from aerona.constants.paths import DATABASE_FILENAME
from aerona.core.errors import ValidationFailedError
from aerona.db.migrations import SCRIPT_LOCATION
from aerona.media.keys import is_original_key, is_sha256, is_valid_key
from aerona.services.divine_will.attachments import MEDIA_PREFIX as ATTACHMENT_PREFIX
from aerona.services.exchange import sanitize_database
from aerona.services.library.facts import read_revision
from aerona.services.world_package import PackageManifest, package_member, parse_manifest

NOT_A_PACKAGE = "This is not a Weavers of the Void universe file."
UNREADABLE = "The file could not be opened as a Weavers of the Void universe file."
NEWER_PACKAGE = "This file was made with a newer edition of Weavers of the Void."
MANIFEST_FIRST = "The file does not begin with its manifest."
ESCAPING_PATH = "The file holds a path that leaves the package: {name}."
NOT_A_FILE = "The file holds an entry that is not a plain file: {name}."
REPEATED = "The file holds the entry {name} twice."
UNKNOWN_MEMBER = "The file holds an entry this edition does not know: {name}."
OVERSIZED_OBJECT = "The file holds an image larger than an image may be: {name}."
INFLATED = "When opened, the file is larger than the import limit (it may be a compression bomb)."
NO_DATABASE = "The file holds no universe database."
MISSING_FILE = "The file lacks {name}, which its manifest lists."
UNLISTED_FILE = "The file holds {name}, which its manifest does not list."
TAMPERED = "The file was changed after it was exported: {name} does not match its recorded size and hash."
CORRUPT = "The universe database in the file is corrupt."
NO_REVISION = "The universe database in the file carries no schema revision."
NEWER_SCHEMA = "The universe database in the file was made by a newer edition of Weavers of the Void."
READ_MODE: Final = "r|gz"
WRITE_MODE: Final = "w:gz"
INTEGRITY_CHECK = "PRAGMA integrity_check"
INTEGRITY_OK = "ok"
UNSAFE_SEGMENTS = frozenset({"", ".", ".."})
PACKED_PREFIXES = (ORIGINALS_PREFIX, f"{ATTACHMENT_PREFIX}/")

Progress = Callable[[int, int], None]


@dataclass(frozen=True)
class PackedFile:
    path: str
    size: int
    sha256: str

    def payload(self) -> dict[str, Any]:
        return {"path": self.path, "size": self.size, "sha256": self.sha256}


@dataclass(frozen=True)
class LibraryManifest:
    universe_id: str
    name: str
    summary: str
    notes: str
    tags: tuple[str, ...]
    created_at: datetime | None
    exported_at: datetime | None
    app_version: str
    schema_revision: str
    epoch: int
    year: int
    population: int
    sons: int
    files: tuple[PackedFile, ...]

    def payload(self) -> dict[str, Any]:
        return {
            "format": LIBRARY_PACKAGE_FORMAT,
            "version": LIBRARY_PACKAGE_VERSION,
            "universe_id": self.universe_id,
            "name": self.name,
            "summary": self.summary,
            "notes": self.notes,
            "tags": list(self.tags),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "exported_at": self.exported_at.isoformat() if self.exported_at else None,
            "app_version": self.app_version,
            "schema_revision": self.schema_revision,
            "epoch": self.epoch,
            "year": self.year,
            "counts": {"population": self.population, "sons": self.sons, "files": len(self.files)},
            "files": [item.payload() for item in self.files],
        }


@dataclass(frozen=True)
class PackagePreview:
    name: str
    summary: str
    notes: str
    tags: tuple[str, ...]
    source_id: str
    created_at: datetime | None
    exported_at: datetime | None
    app_version: str
    schema_revision: str
    epoch: int
    year: int
    population: int
    sons: int
    files: int
    size_bytes: int
    legacy: bool
    dropped: int


@dataclass
class CheckedPackage:
    legacy: PackageManifest
    library: LibraryManifest | None
    staging: Path
    found: dict[str, PackedFile] = field(default_factory=dict)
    dropped: int = 0
    revision: str = ""

    @property
    def database(self) -> Path:
        return self.staging / DATABASE_FILENAME

    def media(self) -> list[PackedFile]:
        return [item for name, item in sorted(self.found.items()) if name.startswith(PACKAGE_MEDIA_MEMBER_PREFIX)]

    def preview(self) -> PackagePreview:
        library = self.library
        legacy = self.legacy
        return PackagePreview(
            name=library.name if library else legacy.name,
            summary=library.summary if library else "",
            notes=library.notes if library else "",
            tags=library.tags if library else (),
            source_id=library.universe_id if library else "",
            created_at=library.created_at if library else None,
            exported_at=library.exported_at if library else parsed_time(legacy.date),
            app_version=library.app_version if library else "",
            schema_revision=self.revision,
            epoch=library.epoch if library else legacy.epoch or 0,
            year=library.year if library else 0,
            population=library.population if library else 0,
            sons=library.sons if library else 0,
            files=len(self.found),
            size_bytes=sum(item.size for item in self.found.values()),
            legacy=library is None,
            dropped=self.dropped,
        )


def parsed_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def whole(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def text_of(value: Any) -> str:
    return value if isinstance(value, str) else ""


def confined(name: str) -> bool:
    if not name or name.startswith("/") or "\\" in name or "\x00" in name:
        return False
    segments = name.split("/")
    return not any(segment in UNSAFE_SEGMENTS for segment in segments) and PurePosixPath(name).as_posix() == name


def packable_key(key: str) -> bool:
    return is_valid_key(key) and any(key.startswith(prefix) for prefix in PACKED_PREFIXES)


def media_member(key: str) -> str:
    return f"{PACKAGE_MEDIA_MEMBER_PREFIX}{key}"


def staged_path(staging: Path, member: str) -> Path:
    if member == PACKAGE_DATABASE_MEMBER:
        return staging / DATABASE_FILENAME
    return staging / STAGED_MEDIA_DIRNAME / member.removeprefix(PACKAGE_MEDIA_MEMBER_PREFIX)


def database_file(path: Path) -> PackedFile:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while block := handle.read(HASH_CHUNK_BYTES):
            digest.update(block)
            size += len(block)
    return PackedFile(path=PACKAGE_DATABASE_MEMBER, size=size, sha256=digest.hexdigest())


def packed_file(raw: Any) -> PackedFile:
    if not isinstance(raw, dict):
        raise ValidationFailedError(NOT_A_PACKAGE)
    path, size, digest = raw.get("path"), raw.get("size"), raw.get("sha256")
    if not isinstance(path, str) or not confined(path):
        raise ValidationFailedError(ESCAPING_PATH.format(name=path))
    if not isinstance(size, int) or isinstance(size, bool) or size < 0 or not isinstance(digest, str) or not is_sha256(digest):
        raise ValidationFailedError(NOT_A_PACKAGE)
    return PackedFile(path=path, size=size, sha256=digest)


def parse_library_manifest(raw: bytes) -> LibraryManifest:
    try:
        data = json.loads(raw)
    except ValueError as error:
        raise ValidationFailedError(NOT_A_PACKAGE) from error
    if not isinstance(data, dict) or data.get("format") != LIBRARY_PACKAGE_FORMAT:
        raise ValidationFailedError(NOT_A_PACKAGE)
    version = data.get("version")
    if not isinstance(version, int) or isinstance(version, bool):
        raise ValidationFailedError(NOT_A_PACKAGE)
    if version > LIBRARY_PACKAGE_VERSION:
        raise ValidationFailedError(NEWER_PACKAGE)
    raw_counts, files, raw_tags = data.get("counts"), data.get("files"), data.get("tags")
    if not isinstance(files, list):
        raise ValidationFailedError(NOT_A_PACKAGE)
    counts: dict[str, Any] = raw_counts if isinstance(raw_counts, dict) else {}
    tags: list[Any] = raw_tags if isinstance(raw_tags, list) else []
    return LibraryManifest(
        universe_id=text_of(data.get("universe_id")),
        name=text_of(data.get("name")),
        summary=text_of(data.get("summary")),
        notes=text_of(data.get("notes")),
        tags=tuple(tag for tag in tags if isinstance(tag, str)),
        created_at=parsed_time(data.get("created_at")),
        exported_at=parsed_time(data.get("exported_at")),
        app_version=text_of(data.get("app_version")),
        schema_revision=text_of(data.get("schema_revision")),
        epoch=whole(data.get("epoch")),
        year=whole(data.get("year")),
        population=whole(counts.get("population")),
        sons=whole(counts.get("sons")),
        files=tuple(packed_file(item) for item in files),
    )


class CountingReader(io.RawIOBase):
    def __init__(self, handle: IO[bytes], seen: Callable[[int], None]) -> None:
        self._handle = handle
        self._seen = seen

    def readable(self) -> bool:
        return True

    def read(self, size: int = -1) -> bytes:
        data = self._handle.read(size)
        self._seen(len(data))
        return data


def add_bytes(archive: tarfile.TarFile, name: str, data: bytes) -> None:
    archive.addfile(package_member(name, len(data)), io.BytesIO(data))


def write_library_package(target: Path, legacy: PackageManifest, manifest: LibraryManifest, staging: Path, progress: Progress) -> None:
    total = sum(item.size for item in manifest.files)
    written = 0

    def seen(count: int) -> None:
        nonlocal written
        written += count
        progress(written, total)

    with tarfile.open(target, WRITE_MODE) as archive:
        add_bytes(archive, PACKAGE_MANIFEST_MEMBER, json.dumps(legacy.payload()).encode())
        add_bytes(archive, LIBRARY_PACKAGE_MEMBER, json.dumps(manifest.payload(), ensure_ascii=False).encode())
        for item in manifest.files:
            with staged_path(staging, item.path).open("rb") as handle:
                archive.addfile(package_member(item.path, item.size), CountingReader(handle, seen))
    progress(total, total)


class StrictReader:
    def __init__(self, staging: Path, inflated_limit: int, progress: Progress, compressed_size: int) -> None:
        self.staging = staging
        self.inflated_limit = inflated_limit
        self.progress = progress
        self.compressed_size = compressed_size
        self.legacy: PackageManifest | None = None
        self.library: LibraryManifest | None = None
        self.found: dict[str, PackedFile] = {}
        self.seen: set[str] = set()
        self.spent = 0

    def read(self, source: Path) -> None:
        try:
            with source.open("rb") as raw, tarfile.open(fileobj=raw, mode=READ_MODE) as archive:
                for member in archive:
                    self.consume(archive, member)
                    self.progress(raw.tell(), self.compressed_size)
        except (tarfile.TarError, zlib.error, EOFError, OSError) as error:
            raise ValidationFailedError(UNREADABLE) from error
        if self.legacy is None:
            raise ValidationFailedError(NOT_A_PACKAGE)
        if PACKAGE_DATABASE_MEMBER not in self.found:
            raise ValidationFailedError(NO_DATABASE)

    def consume(self, archive: tarfile.TarFile, member: tarfile.TarInfo) -> None:
        name = member.name
        if not confined(name):
            raise ValidationFailedError(ESCAPING_PATH.format(name=name))
        if not member.isfile():
            raise ValidationFailedError(NOT_A_FILE.format(name=name))
        if name in self.seen:
            raise ValidationFailedError(REPEATED.format(name=name))
        self.seen.add(name)
        self.spent += member.size
        if self.spent > self.inflated_limit:
            raise ValidationFailedError(INFLATED)
        handle = archive.extractfile(member)
        if handle is None:
            raise ValidationFailedError(NOT_A_FILE.format(name=name))
        if self.legacy is None:
            if name != PACKAGE_MANIFEST_MEMBER:
                raise ValidationFailedError(MANIFEST_FIRST)
            self.legacy = parse_manifest(bounded(handle, PACKAGE_MANIFEST_MAX_BYTES))
        elif name == LIBRARY_PACKAGE_MEMBER:
            self.library = parse_library_manifest(bounded(handle, PACKAGE_MANIFEST_MAX_BYTES))
        elif name == PACKAGE_DATABASE_MEMBER:
            self.found[name] = self.stage(name, handle, self.inflated_limit)
        elif name.startswith(PACKAGE_MEDIA_MEMBER_PREFIX) and packable_key(name.removeprefix(PACKAGE_MEDIA_MEMBER_PREFIX)):
            if member.size > PACKAGE_OBJECT_MAX_BYTES:
                raise ValidationFailedError(OVERSIZED_OBJECT.format(name=name))
            self.found[name] = self.stage(name, handle, PACKAGE_OBJECT_MAX_BYTES)
        else:
            raise ValidationFailedError(UNKNOWN_MEMBER.format(name=name))

    def stage(self, name: str, handle: IO[bytes], limit: int) -> PackedFile:
        target = staged_path(self.staging, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        size = 0
        with target.open("wb") as output:
            while block := handle.read(HASH_CHUNK_BYTES):
                size += len(block)
                if size > limit:
                    raise ValidationFailedError(INFLATED)
                digest.update(block)
                output.write(block)
        return PackedFile(path=name, size=size, sha256=digest.hexdigest())


def bounded(handle: IO[bytes], limit: int) -> bytes:
    data = handle.read(limit + 1)
    if len(data) > limit:
        raise ValidationFailedError(INFLATED)
    return data


def verify_listed(library: LibraryManifest, found: dict[str, PackedFile]) -> None:
    listed = {item.path: item for item in library.files}
    for name in sorted(set(listed) - set(found)):
        raise ValidationFailedError(MISSING_FILE.format(name=name))
    for name in sorted(set(found) - set(listed)):
        raise ValidationFailedError(UNLISTED_FILE.format(name=name))
    for name, item in sorted(found.items()):
        if (item.size, item.sha256) != (listed[name].size, listed[name].sha256):
            raise ValidationFailedError(TAMPERED.format(name=name))


def keep_matching(legacy: PackageManifest, found: dict[str, PackedFile], staging: Path) -> int:
    expected = {media_member(item.key): item for item in legacy.objects}
    dropped = 0
    for name, item in sorted(found.items()):
        if not name.startswith(PACKAGE_MEDIA_MEMBER_PREFIX):
            continue
        wanted = expected.get(name)
        key = name.removeprefix(PACKAGE_MEDIA_MEMBER_PREFIX)
        if wanted is None or not is_original_key(key) or (wanted.size, wanted.sha256) != (item.size, item.sha256):
            staged_path(staging, name).unlink(missing_ok=True)
            del found[name]
            dropped += 1
    return dropped


def known_revision(revision: str) -> bool:
    try:
        return ScriptDirectory(str(SCRIPT_LOCATION)).get_revision(revision) is not None
    except CommandError:
        return False


def check_database(path: Path, *, legacy: bool) -> str:
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            verdict = connection.execute(INTEGRITY_CHECK).fetchone()
        finally:
            connection.close()
    except sqlite3.Error as error:
        raise ValidationFailedError(CORRUPT) from error
    if verdict is None or verdict[0] != INTEGRITY_OK:
        raise ValidationFailedError(CORRUPT)
    revision = read_revision(path)
    if not revision:
        raise ValidationFailedError(NO_REVISION)
    if not known_revision(revision):
        raise ValidationFailedError(NEWER_SCHEMA)
    sanitize_database(path, require_cosmos=legacy)
    return revision


def check_package(source: Path, staging: Path, inflated_limit: int, progress: Progress) -> CheckedPackage:
    reader = StrictReader(staging, inflated_limit, progress, source.stat().st_size)
    reader.read(source)
    assert reader.legacy is not None
    checked = CheckedPackage(legacy=reader.legacy, library=reader.library, staging=staging, found=reader.found)
    if reader.library is not None:
        verify_listed(reader.library, reader.found)
    else:
        checked.dropped = keep_matching(reader.legacy, reader.found, staging)
    checked.revision = check_database(checked.database, legacy=reader.library is None)
    return checked
