import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aerona.constants.library_packages import TRASH_ENTRY_PATTERN, TRASH_NOTE_FILENAME, TRASH_STAMP_FORMAT
from aerona.core.errors import NotFoundError
from aerona.paths import UniversePaths
from aerona.services.library.catalogue import UniverseRecord
from aerona.services.library.manifest import UniverseManifest, read_manifest, write_manifest

NO_SUCH_ENTRY = "No such universe in the trash."
TRASH_ENTRY = re.compile(TRASH_ENTRY_PATTERN)


@dataclass(frozen=True)
class TrashEntry:
    entry_id: str
    folder: Path
    manifest: UniverseManifest
    deleted_at: datetime
    pinned: bool
    cover_path: str | None
    population: int
    sons: int
    size_bytes: int


def entry_id_of(universe_id: str, at: datetime) -> str:
    return f"{universe_id}-{at.astimezone(UTC).strftime(TRASH_STAMP_FORMAT)}"


def note_of(record: UniverseRecord, at: datetime) -> dict[str, object]:
    return {
        "deleted_at": at.isoformat(),
        "pinned": record.pinned,
        "cover_path": record.cover_path,
        "population": record.population,
        "sons": record.sons,
        "size_bytes": record.size_bytes,
    }


def move_to_trash(paths: UniversePaths, trash: Path, record: UniverseRecord, at: datetime) -> str:
    paths.root.mkdir(parents=True, exist_ok=True)
    write_manifest(paths.manifest, record.manifest())
    (paths.root / TRASH_NOTE_FILENAME).write_text(json.dumps(note_of(record, at)), encoding="utf-8")
    trash.mkdir(parents=True, exist_ok=True)
    entry_id = entry_id_of(record.id, at)
    os.replace(paths.root, trash / entry_id)
    return entry_id


def number(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def read_entry(folder: Path) -> TrashEntry | None:
    if not folder.is_dir() or not TRASH_ENTRY.match(folder.name):
        return None
    manifest = read_manifest(UniversePaths(folder).manifest)
    if manifest is None:
        return None
    try:
        note = json.loads((folder / TRASH_NOTE_FILENAME).read_text(encoding="utf-8"))
        deleted_at = datetime.fromisoformat(str(note["deleted_at"]))
    except (OSError, ValueError, KeyError, TypeError):
        note, deleted_at = {}, datetime.fromtimestamp(folder.stat().st_mtime, UTC)
    cover = note.get("cover_path")
    return TrashEntry(
        entry_id=folder.name,
        folder=folder,
        manifest=manifest,
        deleted_at=deleted_at if deleted_at.tzinfo else deleted_at.replace(tzinfo=UTC),
        pinned=bool(note.get("pinned", False)),
        cover_path=cover if isinstance(cover, str) else None,
        population=number(note.get("population")),
        sons=number(note.get("sons")),
        size_bytes=number(note.get("size_bytes")),
    )


def trash_entries(trash: Path) -> list[TrashEntry]:
    if not trash.is_dir():
        return []
    found = [entry for folder in sorted(trash.iterdir()) if (entry := read_entry(folder)) is not None]
    return sorted(found, key=lambda entry: (entry.deleted_at, entry.entry_id), reverse=True)


def find_entry(trash: Path, entry_id: str) -> TrashEntry:
    found = read_entry(trash / entry_id) if TRASH_ENTRY.match(entry_id) else None
    if found is None:
        raise NotFoundError(NO_SUCH_ENTRY)
    return found


def bring_back(entry: TrashEntry, paths: UniversePaths, manifest: UniverseManifest) -> None:
    paths.root.parent.mkdir(parents=True, exist_ok=True)
    os.replace(entry.folder, paths.root)
    (paths.root / TRASH_NOTE_FILENAME).unlink(missing_ok=True)
    write_manifest(paths.manifest, manifest)
