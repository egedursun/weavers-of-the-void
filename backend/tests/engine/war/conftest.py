from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.session import Database
from aerona.engine.context import TickContext
from aerona.engine.primitives.manual import manual_context
from tests.conftest import OpenDatabase
from tests.engine.core.factories import CoreWorld, seed_core_world


@pytest.fixture
async def database(tmp_path: Path, open_database: OpenDatabase) -> AsyncIterator[Database]:
    database = open_database(tmp_path / "war.db")
    yield database
    await database.dispose()


@pytest.fixture
async def session(database: Database) -> AsyncIterator[AsyncSession]:
    async with database.write() as session:
        yield session


@pytest.fixture
async def world(session: AsyncSession) -> CoreWorld:
    return await seed_core_world(session)


@pytest.fixture
async def ctx(session: AsyncSession, world: CoreWorld) -> TickContext:
    return await manual_context(session, "test")
