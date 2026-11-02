import sqlite3
from contextlib import closing
from pathlib import Path

from aerona.migration.legacy.errors import MigrationError

READ_ONLY_URI = "file:{path}?mode=ro"


def take_snapshot(source: Path, destination: Path) -> Path:
    if not source.is_file():
        raise MigrationError(f"No legacy database at {source}.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    with closing(sqlite3.connect(READ_ONLY_URI.format(path=source.resolve()), uri=True)) as origin, closing(sqlite3.connect(destination)) as copy:
        origin.backup(copy)
    return destination
