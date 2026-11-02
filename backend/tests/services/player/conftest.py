from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.session import Database
from aerona.rules.registry import Rules
from aerona.services.player.scope import PlayerScope
from tests.conftest import OpenDatabase
from tests.services.player.factories import PlayerWorld, Recorder, seed_player_world


@pytest.fixture
async def database(tmp_path: Path, open_database: OpenDatabase) -> AsyncIterator[Database]:
    database = open_database(tmp_path / "player.db")
    yield database
    await database.dispose()


@pytest.fixture
async def session(database: Database) -> AsyncIterator[AsyncSession]:
    async with database.write() as session:
        yield session


@pytest.fixture
def rules() -> Rules:
    return Rules()


@pytest.fixture
def recorder() -> Recorder:
    return Recorder()


@pytest.fixture
async def world(session: AsyncSession) -> PlayerWorld:
    return await seed_player_world(session)


@pytest.fixture
def scope(session: AsyncSession, rules: Rules, recorder: Recorder, world: PlayerWorld) -> PlayerScope:
    return PlayerScope(session, rules, recorder.publish)
