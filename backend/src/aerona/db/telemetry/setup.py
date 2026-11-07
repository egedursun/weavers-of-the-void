from pathlib import Path
from typing import Any

from sqlalchemy import Connection, event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from aerona.constants.telemetry import TELEMETRY_DATABASE_FILENAME
from aerona.constants.timeouts import SQLITE_BUSY_TIMEOUT_MS
from aerona.db.inline_sqlite import inline_engine
from aerona.db.telemetry.tables import LiveEventRow, LlmCallRow, TelemetryBase
from aerona.domain.enums.telemetry import LlmCallStatus

ASYNC_DRIVER_PREFIX = "sqlite+aiosqlite:///"
TABLE_DEFINITION_QUERY = "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = :name"
STALE_SUFFIX = "_stale"
WORLD_KEY_COLUMN = "world_key"


def telemetry_url(data_dir: Path) -> str:
    return f"{ASYNC_DRIVER_PREFIX}{data_dir / TELEMETRY_DATABASE_FILENAME}"


def _configure(connection: Any, _record: Any) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
    cursor.close()


def rebuild_stale_calls(connection: Connection) -> None:
    table = LlmCallRow.__tablename__
    definition = connection.execute(text(TABLE_DEFINITION_QUERY), {"name": table}).scalar()
    if definition is None or all(f"'{status.value}'" in definition for status in LlmCallStatus):
        return
    stale = f"{table}{STALE_SUFFIX}"
    calls = TelemetryBase.metadata.tables[table]
    for index in calls.indexes:
        connection.execute(text(f'DROP INDEX IF EXISTS "{index.name}"'))
    connection.execute(text(f'ALTER TABLE "{table}" RENAME TO "{stale}"'))
    TelemetryBase.metadata.create_all(connection, tables=[calls])
    columns = ", ".join(f'"{column.name}"' for column in calls.columns)
    connection.execute(text(f'INSERT INTO "{table}" ({columns}) SELECT {columns} FROM "{stale}"'))
    connection.execute(text(f'DROP TABLE "{stale}"'))


def drop_unowned_events(connection: Connection) -> None:
    table = LiveEventRow.__tablename__
    definition = connection.execute(text(TABLE_DEFINITION_QUERY), {"name": table}).scalar()
    if definition is not None and WORLD_KEY_COLUMN not in definition:
        connection.execute(text(f'DROP TABLE "{table}"'))


def prepare(connection: Connection) -> None:
    rebuild_stale_calls(connection)
    drop_unowned_events(connection)
    TelemetryBase.metadata.create_all(connection)


class TelemetryDatabase:
    def __init__(self, url: str) -> None:
        self.engine: AsyncEngine = inline_engine(url)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        event.listen(self.engine.sync_engine, "connect", _configure)

    async def setup(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(prepare)

    async def dispose(self) -> None:
        await self.engine.dispose()


async def setup_telemetry(url: str) -> TelemetryDatabase:
    database = TelemetryDatabase(url)
    await database.setup()
    return database
