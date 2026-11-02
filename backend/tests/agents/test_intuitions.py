import copy
from typing import Any

from sqlalchemy import select

from aerona.agents.runtime import AgentRuntime
from aerona.agents.world_birth import process_intuitions
from aerona.db.repositories.entities import EntityRepository
from aerona.db.session import Database
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import HorizonIntuitionRow, RouteRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.travel import HorizonStatus, TravelMethod
from aerona.engine.phases.exploration import recover_intuitions
from aerona.llm.errors import LlmError
from aerona.prompts import PromptId, output_model
from aerona.prompts.schemas.base import OutputModel
from tests.agents.fakes import FakeModel
from tests.agents.world import AgentWorld
from tests.prompts.payloads import PAYLOADS


def new_world(**changes: Any) -> OutputModel:
    data = copy.deepcopy(PAYLOADS[PromptId.NEW_WORLD_USER])
    data.update(changes)
    return output_model(PromptId.NEW_WORLD_USER).model_validate(data)


async def add_intuition(database: Database, world: AgentWorld, status: HorizonStatus = HorizonStatus.PENDING) -> int:
    async with database.write() as session:
        row = HorizonIntuitionRow(
            mortal_entity_id=world.core.people.id,
            world_id=world.core.world.id,
            epoch=1,
            how="watching the sky",
            method=TravelMethod.DREAM_JOURNEY,
            status=status,
        )
        session.add(row)
        await session.flush()
        return row.id


async def status_of(database: Database, intuition_id: int) -> HorizonStatus:
    async with database.read() as session:
        row = await session.get(HorizonIntuitionRow, intuition_id)
        assert row is not None
        return row.status


async def test_a_pending_intuition_is_born_and_opens_a_route(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    intuition_id = await add_intuition(database, world)
    model.script(output_model(PromptId.NEW_WORLD_USER), new_world(star_id=None))
    assert await process_intuitions(runtime) == 1
    async with database.read() as session:
        row = await session.get(HorizonIntuitionRow, intuition_id)
        routes = list(await session.scalars(select(RouteRow)))
        worlds = len(list(await session.scalars(select(WorldRow.id))))
    assert row is not None and row.status is HorizonStatus.BORN and row.result_world_id is not None
    assert routes and worlds == 2


async def test_an_intuition_whose_sensor_is_gone_is_wasted(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    intuition_id = await add_intuition(database, world)
    async with database.write() as session:
        people = await session.get(EntityRow, world.core.people.id)
        assert people is not None
        await EntityRepository(session).set_status(people, EntityStatus.DEAD, 2)
    assert await process_intuitions(runtime) == 0
    assert await status_of(database, intuition_id) is HorizonStatus.WASTED
    assert model.calls == []


async def test_a_failed_birth_requeues_the_intuition_and_stops(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    first = await add_intuition(database, world)
    second = await add_intuition(database, world)
    model.script(output_model(PromptId.NEW_WORLD_USER), LlmError("the model failed"))
    assert await process_intuitions(runtime) == 0
    assert await status_of(database, first) is HorizonStatus.PENDING
    assert await status_of(database, second) is HorizonStatus.PENDING
    assert len(model.calls) == 1


async def test_interrupted_intuitions_return_to_pending(database: Database, world: AgentWorld) -> None:
    intuition_id = await add_intuition(database, world, HorizonStatus.PROCESSING)
    async with database.write() as session:
        assert await recover_intuitions(session) == 1
    assert await status_of(database, intuition_id) is HorizonStatus.PENDING
