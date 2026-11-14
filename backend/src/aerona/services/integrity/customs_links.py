from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.customs import MembershipRow, RevivalRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus


async def mend_customs_links(session: AsyncSession, epoch: int) -> int:
    vanished = select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)
    mended = 0
    for statement in (
        update(RevivalRow).where(RevivalRow.ended_epoch.is_(None), RevivalRow.people_entity_id.in_(vanished)).values(ended_epoch=epoch),
        delete(MembershipRow).where(MembershipRow.polity_entity_id.in_(vanished)),
    ):
        result = await session.execute(statement)
        mended += max(0, getattr(result, "rowcount", 0) or 0)
    return mended
