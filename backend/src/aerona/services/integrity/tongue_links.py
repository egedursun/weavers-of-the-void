from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.tongues import DecipherWorkRow, DivineTongueRow, LanguagePolicyRow
from aerona.domain.enums.entity import EntityStatus
from aerona.services.integrity.dominion_links import fallen_gods


async def mend_tongue_links(session: AsyncSession) -> int:
    fallen = await fallen_gods(session)
    gone = select(EntityRow.id).where(EntityRow.status.not_in([EntityStatus.CANON, EntityStatus.DEAD]))
    vanished = select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)
    mended = 0
    statements = [
        delete(LanguagePolicyRow).where(LanguagePolicyRow.holder_entity_id.in_(vanished)),
        delete(LanguagePolicyRow).where(LanguagePolicyRow.language_entity_id.in_(gone)),
        delete(DivineTongueRow).where(DivineTongueRow.god_node_id.in_(fallen)),
        delete(DecipherWorkRow).where(DecipherWorkRow.language_entity_id.in_(gone)),
    ]
    for statement in statements:
        found = await session.execute(statement)
        mended += int(getattr(found, "rowcount", 0) or 0)
    await session.flush()
    return mended
