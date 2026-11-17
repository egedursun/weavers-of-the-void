from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.session import Database
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kind_crafts import GarmentKindRow, ToolKindRow
from aerona.db.tables.kinds import KindHoldingRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.kind_crafts import GarmentCategory, ToolCategory
from aerona.domain.enums.kinds import KindConcept
from aerona.domain.models.entity_stats import ItemStats, PeopleStats
from aerona.engine.kinds.legacy import items_held
from aerona.rules.registry import Rules
from tests.conftest import OpenDatabase
from tests.engine.cosmos.factories import Cosmos, make_entity, seed_cosmos, tick
from tests.tools.factories import connect


@pytest.fixture
async def session(tmp_path: Path, open_database: OpenDatabase) -> AsyncIterator[AsyncSession]:
    database: Database = open_database(tmp_path / "items.db")
    async with database.write() as found:
        yield found
    await database.dispose()


@pytest.fixture
async def cosmos(session: AsyncSession) -> Cosmos:
    return await seed_cosmos(session)


async def owned_item(session: AsyncSession, cosmos: Cosmos, owner: EntityRow, name: str, item_class: ItemClass) -> EntityRow:
    item = await make_entity(session, name, EntityType.ITEM, ItemStats(), world_id=cosmos.home.id)
    session.add(ItemProfileRow(item_entity_id=item.id, item_class=item_class))
    await connect(session, owner.id, item.id, BondKind.OWNS)
    await session.flush()
    return item


async def test_items_of_tool_and_worn_classes_become_kinds_their_people_hold(session: AsyncSession, cosmos: Cosmos) -> None:
    people = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=900), world_id=cosmos.home.id)
    await owned_item(session, cosmos, people, "Ridge Adze", ItemClass.TOOL)
    await owned_item(session, cosmos, people, "Second Adze", ItemClass.TOOL)
    await owned_item(session, cosmos, people, "Grey Mantle", ItemClass.CLOAK)
    await owned_item(session, cosmos, people, "Plain Blade", ItemClass.BLADE)
    assert await items_held(tick(session, Rules())) == 2
    tools = list(await session.scalars(select(ToolKindRow)))
    garments = list(await session.scalars(select(GarmentKindRow)))
    assert [(row.name, row.category, row.origin_node_id) for row in tools] == [("Ridge Adze", ToolCategory.CRAFTING, people.id)]
    assert [(row.name, row.category) for row in garments] == [("Grey Mantle", GarmentCategory.OUTER_LAYER)]
    held = {(row.concept, row.kind_id) for row in await session.scalars(select(KindHoldingRow).where(KindHoldingRow.holder_node_id == people.id))}
    assert held == {(KindConcept.TOOL, tools[0].id), (KindConcept.GARMENT, garments[0].id)}
