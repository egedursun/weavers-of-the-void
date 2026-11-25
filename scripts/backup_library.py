import argparse
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

LIBRARY_DATABASE = "library.db"
UNIVERSES = "universes"
UNIVERSE_DATABASE = "aerona.db"
SKIPPED_SUFFIXES = (".db-wal", ".db-shm", ".lock")
SKIPPED_FOLDERS = frozenset({"work", "forecasts"})


@dataclass(frozen=True)
class Copied:
    databases: int
    files: int
    bytes: int


def backup_database(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    reader = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    writer = sqlite3.connect(target)
    try:
        reader.backup(writer)
    finally:
        writer.close()
        reader.close()


def kept(path: Path, universe: Path) -> bool:
    relative = path.relative_to(universe)
    if relative.parts and relative.parts[0] in SKIPPED_FOLDERS:
        return False
    return path.name != UNIVERSE_DATABASE and not path.name.endswith(SKIPPED_SUFFIXES)


def backup_universe(universe: Path, target: Path) -> Copied:
    databases = 0
    files = 0
    size = 0
    database = universe / UNIVERSE_DATABASE
    if database.exists():
        backup_database(database, target / UNIVERSE_DATABASE)
        databases += 1
        size += (target / UNIVERSE_DATABASE).stat().st_size
    for path in sorted(universe.rglob("*")):
        if not path.is_file() or not kept(path, universe):
            continue
        destination = target / path.relative_to(universe)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        files += 1
        size += destination.stat().st_size
    return Copied(databases, files, size)


def backup_library(data_dir: Path, target: Path) -> Copied:
    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"{target} is not empty; choose a new folder for the backup.")
    target.mkdir(parents=True, exist_ok=True)
    databases = 0
    files = 0
    size = 0
    catalogue = data_dir / LIBRARY_DATABASE
    if catalogue.exists():
        backup_database(catalogue, target / LIBRARY_DATABASE)
        databases += 1
        size += (target / LIBRARY_DATABASE).stat().st_size
    root = data_dir / UNIVERSES
    for universe in sorted(path for path in root.iterdir() if path.is_dir()) if root.exists() else []:
        copied = backup_universe(universe, target / UNIVERSES / universe.name)
        databases += copied.databases
        files += copied.files
        size += copied.bytes
    return Copied(databases, files, size)


def main() -> int:
    parser = argparse.ArgumentParser(description="Back up the whole library of universes while the app runs.")
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("target", type=Path, nargs="?")
    arguments = parser.parse_args()
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    target = arguments.target or arguments.data_dir.parent / f"library-backup-{stamp}"
    copied = backup_library(arguments.data_dir, target)
    print(f"backed up {copied.databases} databases and {copied.files} files ({copied.bytes} bytes) into {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
