from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from aerona.db.session import Database
from tests.conftest import OpenDatabase
from tests.tools.factories import Cosmos, seed_cosmos


@pytest.fixture
async def database(tmp_path: Path, open_database: OpenDatabase) -> AsyncIterator[Database]:
    database = open_database(tmp_path / "tools.db")
    yield database
    await database.dispose()


@pytest.fixture
async def cosmos(database: Database) -> Cosmos:
    async with database.write() as session:
        return await seed_cosmos(session)
