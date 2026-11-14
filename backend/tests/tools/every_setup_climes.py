from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.climes import CosmopolitanCultureRow
from aerona.db.tables.entities import EntityRow
from tests.tools.every_tool import Ids
from tests.tools.factories import Realm


async def road_culture(session: AsyncSession, realm: Realm) -> Ids:
    me = await session.get(EntityRow, realm.mortal_id)
    assert me is not None
    me.location_id = realm.settlement_id
    culture = CosmopolitanCultureRow(name="The Folk of the Long Road", values={"tradition": 20}, formed_epoch=0, locked=[])
    session.add(culture)
    await session.flush()
    return {"culture": culture.id}
