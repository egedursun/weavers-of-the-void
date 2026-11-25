import importlib.util
import sqlite3
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("backup_library", REPOSITORY_ROOT / "scripts" / "backup_library.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["backup_library"] = module
    spec.loader.exec_module(module)
    return module


def database(path: Path, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("pragma journal_mode=wal")
    connection.execute("create table notes (text text)")
    connection.executemany("insert into notes values (?)", [(row,) for row in rows])
    connection.commit()
    connection.close()


def notes(path: Path) -> list[str]:
    connection = sqlite3.connect(path)
    try:
        return [row[0] for row in connection.execute("select text from notes order by rowid")]
    finally:
        connection.close()


def test_the_whole_library_is_backed_up_with_every_universe_and_its_files(tmp_path: Path) -> None:
    data = tmp_path / "data"
    database(data / "library.db", ["catalogue"])
    database(data / "universes" / "aaaa" / "aerona.db", ["first"])
    database(data / "universes" / "bbbb" / "aerona.db", ["second", "third"])
    (data / "universes" / "aaaa" / "media" / "originals").mkdir(parents=True)
    (data / "universes" / "aaaa" / "media" / "originals" / "a.png").write_bytes(b"png")
    (data / "universes" / "aaaa" / "work").mkdir()
    (data / "universes" / "aaaa" / "work" / "temp.bin").write_bytes(b"temp")
    target = tmp_path / "backup"
    copied = script().backup_library(data, target)
    assert copied.databases == 3
    assert notes(target / "library.db") == ["catalogue"]
    assert notes(target / "universes" / "bbbb" / "aerona.db") == ["second", "third"]
    assert (target / "universes" / "aaaa" / "media" / "originals" / "a.png").read_bytes() == b"png"
    assert not (target / "universes" / "aaaa" / "work").exists()
    assert not list(target.rglob("*.db-wal"))


def test_a_backup_never_writes_into_a_folder_that_holds_files(tmp_path: Path) -> None:
    data = tmp_path / "data"
    database(data / "library.db", ["catalogue"])
    target = tmp_path / "backup"
    target.mkdir()
    (target / "keep.txt").write_text("mine")
    with pytest.raises(SystemExit):
        script().backup_library(data, target)
    assert (target / "keep.txt").read_text() == "mine"
