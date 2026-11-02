from sqlalchemy import text

from aerona.constants.timeouts import SQLITE_BUSY_TIMEOUT_MS
from aerona.db.session import Database

EXPECTED_PRAGMAS = {
    "journal_mode": "wal",
    "synchronous": 1,
    "foreign_keys": 1,
    "busy_timeout": SQLITE_BUSY_TIMEOUT_MS,
    "trusted_schema": 0,
}


async def test_every_connection_applies_the_safety_pragmas(database: Database) -> None:
    async with database.read() as session:
        for name, expected in EXPECTED_PRAGMAS.items():
            assert await session.scalar(text(f"PRAGMA {name}")) == expected, name
