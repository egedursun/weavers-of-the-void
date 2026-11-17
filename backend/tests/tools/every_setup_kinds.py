from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.kinds import GoodKindRow
from aerona.domain.enums.kinds import GoodCategory
from tests.tools.every_setup import ruler
from tests.tools.every_setup_crafts import people_home
from tests.tools.factories import Realm

Ids = dict[str, int]


async def good_kind(session: AsyncSession, realm: Realm) -> Ids:
    row = GoodKindRow(name="Ember Loaf", category=GoodCategory.GRAIN, world_id=realm.cosmos.world_id, created_epoch=0, locked=[])
    session.add(row)
    await session.flush()
    return {"good_kind": row.id}


async def kind_at_home(session: AsyncSession, realm: Realm) -> Ids:
    return {**await people_home(session, realm), **await good_kind(session, realm)}


async def kind_under_rule(session: AsyncSession, realm: Realm) -> Ids:
    return {**await ruler(session, realm), **await good_kind(session, realm)}
