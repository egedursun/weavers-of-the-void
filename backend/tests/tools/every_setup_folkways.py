from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import PurificationRow, PurityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.folkways import Purification, PurityState
from aerona.domain.models.entity_stats import ItemStats
from tests.tools.every_setup import second_mortal
from tests.tools.factories import Realm, connect, make_entity

Ids = dict[str, int]


async def owned_item(session: AsyncSession, realm: Realm) -> Ids:
    item = await make_entity(session, "Knotted Cord", EntityType.ITEM, world_id=realm.cosmos.world_id, location_id=realm.settlement_id, stats=ItemStats())
    session.add(ItemProfileRow(item_entity_id=item.id, item_class=ItemClass.RING, locked=[]))
    await connect(session, realm.mortal_id, item.id, BondKind.OWNS)
    await session.flush()
    return {"item": item.id}


async def impure_mortal(session: AsyncSession, realm: Realm) -> Ids:
    town = await session.get(EntityRow, realm.settlement_id)
    assert town is not None
    town.affiliated_entity_id = realm.people_id
    await connect(session, realm.settlement_id, realm.people_id, BondKind.DESCENDS_FROM)
    session.add(PurityRow(holder_node_id=realm.mortal_id, state=PurityState.IMPURE, since_epoch=0, locked=[]))
    session.add(PurificationRow(people_entity_id=realm.people_id, method=Purification.WASHING, epochs=0, cost=0, success=100, locked=[]))
    await session.flush()
    return {}


async def neighbour(session: AsyncSession, realm: Realm) -> Ids:
    found = await second_mortal(session, realm)
    me = await session.get(EntityRow, realm.mortal_id)
    assert me is not None
    me.location_id = realm.settlement_id
    await session.flush()
    return found
