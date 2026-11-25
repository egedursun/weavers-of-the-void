import hashlib
import io
import json
import shutil
import tarfile
import time
import zlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any, Final

from aerona.constants.maintenance import (
    PACKAGE_COPY_BUFFER_BYTES,
    PACKAGE_DATABASE_MEMBER,
    PACKAGE_FORMAT,
    PACKAGE_MANIFEST_MAX_BYTES,
    PACKAGE_MANIFEST_MEMBER,
    PACKAGE_MAX_DECOMPRESSED_BYTES,
    PACKAGE_MEDIA_MEMBER_PREFIX,
    PACKAGE_OBJECT_MAX_BYTES,
    PACKAGE_VERSION,
)
from aerona.core.errors import ValidationFailedError
from aerona.media.errors import MediaStoreError
from aerona.media.keys import is_original_key, is_sha256

NOT_A_PACKAGE = "This is not a Weavers of the Void world file."
UNREADABLE = "This is not a Weavers of the Void world file (could not be opened)."
NEWER_VERSION = "This file was made with a newer Weavers of the Void version."
NO_DATABASE = "The file holds no world database."
BOMB = "When opened, the file is too large (it may be a compression bomb)."
VANISHED = "An image disappeared from the media store during the export."
WRITE_MODE: Final = "w:gz"
READ_MODE: Final = "r|gz"
FILE_MODE = 0o644

ObjectOpener = Callable[[str], io.RawIOBase | None]
ObjectSink = Callable[[str, bytes, str], None]


@dataclass(frozen=True)
class PackagedObject:
    key: str
    sha256: str
    size: int


@dataclass(frozen=True)
class PackageManifest:
    name: str
    epoch: int | None
    creator: str | None
    date: str
    objects: tuple[PackagedObject, ...] = ()

    def payload(self) -> dict[str, Any]:
        return {
            "format": PACKAGE_FORMAT,
            "version": PACKAGE_VERSION,
            "name": self.name,
            "epoch": self.epoch,
            "creator": self.creator,
            "date": self.date,
            "objects": [{"key": item.key, "sha256": item.sha256, "size": item.size} for item in self.objects],
        }


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _objects(raw: Any) -> tuple[PackagedObject, ...]:
    if not isinstance(raw, list):
        return ()
    found: list[PackagedObject] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        key, digest, size = item.get("key"), item.get("sha256"), _optional_int(item.get("size"))
        if isinstance(key, str) and is_original_key(key) and isinstance(digest, str) and is_sha256(digest) and size is not None and size >= 0:
            found.append(PackagedObject(key, digest, size))
    return tuple(found)


def parse_manifest(raw: bytes) -> PackageManifest:
    try:
        data = json.loads(raw)
    except ValueError as error:
        raise ValidationFailedError(NOT_A_PACKAGE) from error
    if not isinstance(data, dict) or data.get("format") != PACKAGE_FORMAT:
        raise ValidationFailedError(NOT_A_PACKAGE)
    version = _optional_int(data.get("version"))
    if version is None:
        raise ValidationFailedError(NOT_A_PACKAGE)
    if version > PACKAGE_VERSION:
        raise ValidationFailedError(NEWER_VERSION)
    return PackageManifest(
        name=_optional_str(data.get("name")) or "",
        epoch=_optional_int(data.get("epoch")),
        creator=_optional_str(data.get("creator")),
        date=_optional_str(data.get("date")) or "",
        objects=_objects(data.get("objects")),
    )


def package_member(name: str, size: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = size
    info.mtime = int(time.time())
    info.mode = FILE_MODE
    return info


def write_package(target: Path, manifest: PackageManifest, database: Path, open_object: ObjectOpener) -> None:
    encoded = json.dumps(manifest.payload()).encode()
    with tarfile.open(target, WRITE_MODE) as archive:
        archive.addfile(package_member(PACKAGE_MANIFEST_MEMBER, len(encoded)), io.BytesIO(encoded))
        with database.open("rb") as handle:
            archive.addfile(package_member(PACKAGE_DATABASE_MEMBER, database.stat().st_size), handle)
        for item in manifest.objects:
            reader = open_object(item.key)
            if reader is None:
                raise MediaStoreError(VANISHED)
            with reader:
                archive.addfile(package_member(f"{PACKAGE_MEDIA_MEMBER_PREFIX}{item.key}", item.size), reader)


def _read_member(handle: IO[bytes], limit: int) -> bytes:
    data = handle.read(limit + 1)
    if len(data) > limit:
        raise ValidationFailedError(BOMB)
    return data


class PackageReader:
    def __init__(self, database_target: Path, receive: ObjectSink) -> None:
        self._database_target = database_target
        self._receive = receive
        self._spent = 0
        self.manifest: PackageManifest | None = None
        self.database_seen = False
        self._expected: dict[str, PackagedObject] = {}

    def read(self, source: IO[bytes]) -> PackageManifest:
        try:
            with tarfile.open(fileobj=source, mode=READ_MODE) as archive:
                for member in archive:
                    self._consume(archive, member)
        except (tarfile.TarError, zlib.error, EOFError) as error:
            raise ValidationFailedError(UNREADABLE) from error
        if self.manifest is None:
            raise ValidationFailedError(NOT_A_PACKAGE)
        if not self.database_seen:
            raise ValidationFailedError(NO_DATABASE)
        return self.manifest

    def _consume(self, archive: tarfile.TarFile, member: tarfile.TarInfo) -> None:
        if not member.isfile():
            return
        self._spent += member.size
        if self._spent > PACKAGE_MAX_DECOMPRESSED_BYTES:
            raise ValidationFailedError(BOMB)
        handle = archive.extractfile(member)
        if handle is None:
            return
        if self.manifest is None:
            if member.name != PACKAGE_MANIFEST_MEMBER:
                raise ValidationFailedError(NOT_A_PACKAGE)
            self.manifest = parse_manifest(_read_member(handle, PACKAGE_MANIFEST_MAX_BYTES))
            self._expected = {item.key: item for item in self.manifest.objects}
        elif member.name == PACKAGE_DATABASE_MEMBER and not self.database_seen:
            with self._database_target.open("wb") as output:
                shutil.copyfileobj(handle, output, PACKAGE_COPY_BUFFER_BYTES)
            self.database_seen = True
        elif member.name.startswith(PACKAGE_MEDIA_MEMBER_PREFIX):
            self._object(member, handle)

    def _object(self, member: tarfile.TarInfo, handle: IO[bytes]) -> None:
        key = member.name.removeprefix(PACKAGE_MEDIA_MEMBER_PREFIX)
        expected = self._expected.pop(key, None)
        if expected is None or member.size > PACKAGE_OBJECT_MAX_BYTES:
            return
        data = _read_member(handle, PACKAGE_OBJECT_MAX_BYTES)
        digest = hashlib.sha256(data).hexdigest()
        if len(data) == expected.size and digest == expected.sha256:
            self._receive(key, data, digest)


def read_package(source: IO[bytes], database_target: Path, receive: ObjectSink) -> PackageManifest:
    return PackageReader(database_target, receive).read(source)
