import shutil
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import text

from aerona.db.session import Database
from aerona.media.file_store import FileMediaStore
from aerona.rules.registry import Rules
from aerona.services.backups import BackupService
from aerona.settings import Settings
from tests.conftest import OpenDatabase

MARK_TABLE = "CREATE TABLE swap_mark (word TEXT)"


def marked(path: Path, word: str) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute("DROP TABLE IF EXISTS swap_mark")
        connection.execute(MARK_TABLE)
        connection.execute("INSERT INTO swap_mark VALUES (?)", (word,))
        connection.commit()
    finally:
        connection.close()


async def read_mark(database: Database) -> str:
    async with database.read() as session:
        return str(await session.scalar(text("SELECT word FROM swap_mark")))


async def test_a_reader_that_slips_in_while_the_file_is_swapped_never_keeps_the_old_file(
    tmp_path: Path, open_database: OpenDatabase, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(data_dir=tmp_path / "data", llm_enabled=False)
    settings.ensure_directories()
    database = open_database(settings.database_path)
    incoming = tmp_path / "incoming.db"
    shutil.copyfile(settings.database_path, incoming)
    marked(settings.database_path, "old")
    marked(incoming, "new")
    assert await read_mark(database) == "old"
    original = Database.dispose

    async def dispose_then_read(self: Database) -> None:
        await original(self)
        await read_mark(self)

    monkeypatch.setattr(Database, "dispose", dispose_then_read)
    backups = BackupService(settings, database, Rules, store=FileMediaStore(settings.media_dir))
    await backups.load_file(incoming)
    monkeypatch.setattr(Database, "dispose", original)
    assert await read_mark(database) == "new"
    await database.dispose()
