from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession

import aerona.db.tables
from aerona.db.base import Base
from aerona.db.session import Database
from tests.engine.core.factories import CoreWorld, seed_core_world

TABLES = aerona.db.tables


@pytest.fixture
async def database(tmp_path: Path) -> AsyncIterator[Database]:
    path = tmp_path / "port.db"
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    engine.dispose()
    database = Database(f"sqlite+aiosqlite:///{path}")
    yield database
    await database.dispose()


@pytest.fixture
async def session(database: Database) -> AsyncIterator[AsyncSession]:
    async with database.write() as session:
        yield session


@pytest.fixture
async def world(session: AsyncSession) -> CoreWorld:
    return await seed_core_world(session)
