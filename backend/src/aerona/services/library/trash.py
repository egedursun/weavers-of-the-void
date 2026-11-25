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
    workspace_id: int | None = None
    deleted_by: int | None = None
    hidden_from: tuple[int, ...] = ()


def entry_id_of(universe_id: str, at: datetime) -> str:
    return f"{universe_id}-{at.astimezone(UTC).strftime(TRASH_STAMP_FORMAT)}"


def note_of(record: UniverseRecord, at: datetime, deleted_by: int | None = None, hidden_from: tuple[int, ...] = ()) -> dict[str, object]:
    return {
        "deleted_at": at.isoformat(),
        "pinned": record.pinned,
        "cover_path": record.cover_path,
        "population": record.population,
        "sons": record.sons,
        "size_bytes": record.size_bytes,
        "workspace_id": record.workspace_id,
        "deleted_by": deleted_by,
        "hidden_from": list(hidden_from),
    }


def move_to_trash(
    paths: UniversePaths, trash: Path, record: UniverseRecord, at: datetime, *, deleted_by: int | None = None, hidden_from: tuple[int, ...] = ()
) -> str:
    paths.root.mkdir(parents=True, exist_ok=True)
    write_manifest(paths.manifest, record.manifest())
    (paths.root / TRASH_NOTE_FILENAME).write_text(json.dumps(note_of(record, at, deleted_by, hidden_from)), encoding="utf-8")
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
        workspace_id=number(note.get("workspace_id")) or None,
        deleted_by=number(note.get("deleted_by")) or None,
        hidden_from=tuple(number(item) for item in note.get("hidden_from") or () if number(item)),
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


def set_entry_workspace(entry: TrashEntry, workspace_id: int) -> None:
    note_path = entry.folder / TRASH_NOTE_FILENAME
    try:
        note = json.loads(note_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        note = {}
    if not isinstance(note, dict):
        note = {}
    note.setdefault("deleted_at", entry.deleted_at.isoformat())
    note["workspace_id"] = workspace_id
    note_path.write_text(json.dumps(note), encoding="utf-8")


def stamp_workspace(trash: Path, workspace_id: int) -> int:
    unstamped = [entry for entry in trash_entries(trash) if entry.workspace_id is None]
    for entry in unstamped:
        set_entry_workspace(entry, workspace_id)
    return len(unstamped)
