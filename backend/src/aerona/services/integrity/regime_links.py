from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.regime import (
    CoalitionMemberRow,
    PatronageTieRow,
    PowerBaseRow,
    RegimeRow,
    SchoolLineageRow,
    SchoolMemberRow,
)
from aerona.domain.enums.entity import EntityStatus


async def mend_regime_links(session: AsyncSession) -> int:
    vanished = select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)
    statements = [
        delete(CoalitionMemberRow).where(CoalitionMemberRow.mortal_entity_id.in_(vanished)),
        delete(PatronageTieRow).where(PatronageTieRow.client_entity_id.in_(vanished)),
        delete(PowerBaseRow).where(PowerBaseRow.mortal_entity_id.in_(vanished)),
        delete(RegimeRow).where(RegimeRow.polity_entity_id.in_(vanished)),
        update(SchoolMemberRow).where(SchoolMemberRow.master_entity_id.in_(vanished)).values(master_entity_id=None),
        update(SchoolLineageRow).where(SchoolLineageRow.doctrine_entity_id.in_(vanished)).values(doctrine_entity_id=None),
    ]
    mended = 0
    for statement in statements:
        found = await session.execute(statement)
        mended += int(getattr(found, "rowcount", 0) or 0)
    await session.flush()
    return mended
