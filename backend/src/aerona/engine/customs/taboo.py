from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.customs import NamingCustomRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.body.customs import people_of


async def name_tabooed(session: AsyncSession, bearer_id: int, epoch: int) -> bool:
    bearer = await session.get(EntityRow, bearer_id)
    if bearer is None or bearer.status is not EntityStatus.DEAD or bearer.end_epoch is None:
        return False
    folk = await people_of(session, bearer)
    custom = await session.get(NamingCustomRow, folk.id) if folk is not None else None
    return custom is not None and epoch - bearer.end_epoch < custom.taboo_epochs
