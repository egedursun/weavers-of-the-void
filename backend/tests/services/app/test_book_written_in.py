import json

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.entity_detail import entity_detail
from aerona.agents.context.scope import load_scope
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.changes import StateChangeRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.node import ActorKind
from aerona.rules.registry import Rules
from aerona.services.books.model import BookBuilder
from tests.services.app.factories import Cosmos, make_entity


async def test_an_entry_tells_the_epoch_its_description_was_written_when_the_life_went_on_after_it(session: AsyncSession, world: Cosmos) -> None:
    chief = await make_entity(session, "Hastle", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    chief.description = "Hastle is a young chief."
    chief.birth_epoch, chief.status, chief.end_epoch = 2, EntityStatus.DEAD, 9
    session.add(
        StateChangeRow(
            epoch=3,
            table_name="entities",
            row_key=json.dumps({"id": chief.id}),
            node_id=chief.id,
            operation=LedgerOperation.UPDATE,
            field="description",
            before_text="Hastle, a child.",
            after_text=chief.description,
            actor_kind=ActorKind.SYSTEM,
        )
    )
    fresh = await make_entity(session, "Ama", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    cosmos = await CosmosRepository(session).get()
    assert cosmos is not None
    fresh.birth_epoch = cosmos.epoch
    await session.flush()
    builder = BookBuilder(session, Rules())
    await builder.load_common()
    assert (await builder.entity_article(chief)).written_in == 3
    assert (await builder.entity_article(fresh)).written_in is None


async def test_the_model_reads_when_a_description_was_written_and_from_which_epoch_a_record_is(session: AsyncSession, world: Cosmos) -> None:
    chief = await make_entity(session, "Hastle", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    chief.description, chief.birth_epoch = "Hastle is a young chief.", 2
    await session.flush()
    told = await entity_detail(await load_scope(session, Rules()), chief)
    assert "from epoch 2" in told and "Age 2" not in told
    assert "as written in epoch 2" in told
