from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.crafts import InsurancePolicyRow, InsurerRow, PublicClockRow, SympatheticLinkRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus


async def mend_crafts_links(session: AsyncSession) -> int:
    vanished = select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)
    mended = 0
    for statement in (
        update(InsurancePolicyRow).where(InsurancePolicyRow.active.is_(True), InsurancePolicyRow.insurer_entity_id.in_(vanished)).values(active=False),
        update(InsurerRow).where(InsurerRow.ruined.is_(False), InsurerRow.insurer_entity_id.in_(vanished)).values(ruined=True),
        delete(SympatheticLinkRow).where(SympatheticLinkRow.holder_node_id.in_(vanished)),
        delete(PublicClockRow).where(PublicClockRow.settlement_entity_id.in_(vanished)),
    ):
        result = await session.execute(statement)
        mended += max(0, getattr(result, "rowcount", 0) or 0)
    return mended
