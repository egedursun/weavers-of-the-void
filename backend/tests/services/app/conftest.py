from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from aerona.db.fast_session import FastSession
from aerona.db.session import Database
from aerona.events.bus import EventBus
from aerona.rules.registry import Rules
from tests.conftest import OpenDatabase
from tests.services.app.factories import Cosmos, seed_cosmos


@pytest.fixture
async def database(tmp_path: Path, open_database: OpenDatabase) -> AsyncIterator[Database]:
    database = open_database(tmp_path / "services.db")
    yield database
    await database.dispose()


@pytest.fixture
async def session(database: Database) -> AsyncIterator[AsyncSession]:
    async with database.gate.held(), async_sessionmaker(database.engine, class_=FastSession, expire_on_commit=False)() as session:
        yield session
        await session.commit()


@pytest.fixture
def rules() -> Rules:
    return Rules()


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


@pytest.fixture
async def world(session: AsyncSession) -> Cosmos:
    seeded = await seed_cosmos(session)
    await session.commit()
    return seeded
