from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from aerona.db.session import Database
from tests.conftest import OpenDatabase


@pytest.fixture
async def database(tmp_path: Path, open_database: OpenDatabase) -> AsyncIterator[Database]:
    database = open_database(tmp_path / "integration.db")
    yield database
    await database.dispose()
