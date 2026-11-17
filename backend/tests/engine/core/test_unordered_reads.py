import hashlib
import sqlite3
from pathlib import Path
from typing import Any

from sqlalchemy import Float, event, select

from aerona.db.base import Base
from aerona.db.session import Database
from aerona.db.types import UtcDateTime
from aerona.engine.pipeline import simulate
from aerona.rules.registry import Rules
from tests.conftest import OpenDatabase
from tests.engine.core.stirring import eager, stir
from tests.engine.integration.factories import seed_rich_cosmos

EPOCHS = 1
TIMINGS = frozenset({"seconds", "elapsed_seconds", "duration_seconds", "phase_seconds"})


def reversed_reads(database: Database) -> Database:
    @event.listens_for(database.engine.sync_engine, "connect")
    def reverse(connection: Any, _record: Any) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA reverse_unordered_selects = ON")
        cursor.close()

    return database


async def digests(database: Database) -> dict[str, str]:
    found: dict[str, str] = {}
    async with database.read() as session:
        for table in Base.metadata.sorted_tables:
            columns = [
                column
                for column in table.columns
                if not isinstance(column.type, UtcDateTime) and column.name not in TIMINGS and not (isinstance(column.type, Float) and "second" in column.name)
            ]
            hashed = hashlib.sha256()
            for row in await session.execute(select(*columns).order_by(*columns)):
                hashed.update(repr(tuple(row)).encode())
            found[table.name] = hashed.hexdigest()
    return found


def copy_file(source: Path, target: Path) -> None:
    with sqlite3.connect(source) as origin, sqlite3.connect(target) as copy:
        origin.backup(copy)


async def test_an_epoch_lives_the_same_whatever_order_unordered_reads_come_back_in(tmp_path: Path, open_database: OpenDatabase) -> None:
    first_path, second_path = tmp_path / "forward.db", tmp_path / "reversed.db"
    seeded = open_database(first_path)
    async with seeded.write() as session:
        await stir(session, await seed_rich_cosmos(session))
    await seeded.dispose()
    copy_file(first_path, second_path)
    forward, backward = open_database(first_path), reversed_reads(open_database(second_path))
    await simulate(forward, EPOCHS, rules=eager(Rules()))
    await simulate(backward, EPOCHS, rules=eager(Rules()))
    ahead, behind = await digests(forward), await digests(backward)
    await forward.dispose()
    await backward.dispose()
    assert sorted(name for name in ahead if ahead[name] != behind[name]) == []
