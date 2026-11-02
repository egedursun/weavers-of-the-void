from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.ledger import LedgerEntryRow
from aerona.domain.enums.entity import EntityType
from tests.tools.factories import DESCRIPTION, Cosmos, count_rows, make_son, son_toolkit


async def test_son_creates_a_place(database: Database, cosmos: Cosmos) -> None:
    async with database.write() as session:
        son = await make_son(session, "Thalor", world_id=cosmos.world_id)
        son_id = son.id
    toolkit = await son_toolkit(database, son_id)
    outcome = await toolkit.runtime.call(
        "create_place",
        {
            "name": "Brinehollow",
            "description": DESCRIPTION,
            "power_level": 2,
            "domain": "Sea",
            "location_id": f"#{cosmos.region_id}",
            "links": [{"target_kind": "entity", "target_id": cosmos.region_id, "kind": "related", "description": "carved from its shore"}],
        },
    )
    assert not outcome.is_error, outcome.text
    assert "Brinehollow" in outcome.text
    async with database.read() as session:
        created = await session.get(EntityRow, toolkit.created_entity_ids[0])
        assert created is not None
        assert created.entity_type is EntityType.PLACE
        assert created.location_id == cosmos.region_id
    assert await count_rows(database, LedgerEntryRow) == 1
