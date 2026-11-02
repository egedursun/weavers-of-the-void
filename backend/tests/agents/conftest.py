from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from aerona.agents.ports import bus_publisher
from aerona.agents.runtime import AgentRuntime
from aerona.db.session import Database
from aerona.events.bus import EventBus
from aerona.rules.registry import Rules
from aerona.rules.registry.model import ModelRules
from tests.agents.fakes import FakeModel
from tests.agents.world import AgentWorld, seed_agent_world
from tests.conftest import OpenDatabase


@pytest.fixture
def rules() -> Rules:
    return Rules(model=ModelRules(retry_wait_1=0, retry_wait_2=0, retry_wait_3=0, restart_wait=0, continuation_wait=0))


@pytest.fixture
async def database(tmp_path: Path, open_database: OpenDatabase) -> AsyncIterator[Database]:
    database = open_database(tmp_path / "agents.db")
    yield database
    await database.dispose()


@pytest.fixture
async def world(database: Database, rules: Rules) -> AgentWorld:
    async with database.write() as session:
        return await seed_agent_world(session, rules)


@pytest.fixture
def model() -> FakeModel:
    return FakeModel()


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


@pytest.fixture
def runtime(database: Database, model: FakeModel, bus: EventBus, world: AgentWorld) -> AgentRuntime:
    return AgentRuntime(database=database, model=model, publish=bus_publisher(bus))
