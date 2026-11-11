from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.arcana import LabTextRow, LawUpkeepRow, LongevityRow, VisStockRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mythic import CosmicOfficeRow, HeroquestRow, MantlingRow, ServitorRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.mythic import HeroquestState, MantlingState
from aerona.services.integrity.dominion_links import fallen_gods


async def mend_mythic_links(session: AsyncSession) -> int:
    fallen = await fallen_gods(session)
    gone = select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)
    open_quests = HeroquestRow.state.in_([HeroquestState.QUESTING, HeroquestState.TRAPPED])
    mended = 0
    statements = [
        delete(ServitorRow).where(ServitorRow.spirit_entity_id.in_(gone)),
        delete(ServitorRow).where(ServitorRow.god_node_id.in_(fallen)),
        update(CosmicOfficeRow).where(CosmicOfficeRow.holder_node_id.in_(fallen)).values(holder_node_id=None, since_epoch=None),
        update(MantlingRow).where(MantlingRow.god_node_id.in_(fallen), MantlingRow.state == MantlingState.WALKING).values(god_node_id=None),
        update(MantlingRow).where(MantlingRow.mortal_entity_id.in_(gone), MantlingRow.state == MantlingState.WALKING).values(state=MantlingState.FAILED),
        update(HeroquestRow).where(and_(HeroquestRow.quester_entity_id.in_(gone), open_quests)).values(state=HeroquestState.FAILED),
        delete(LongevityRow).where(LongevityRow.mortal_entity_id.in_(gone)),
        delete(LabTextRow).where(LabTextRow.book_entity_id.in_(gone)),
        delete(LawUpkeepRow).where(LawUpkeepRow.law_entity_id.in_(gone)),
        delete(VisStockRow).where(VisStockRow.holder_node_id.in_(gone)),
    ]
    for statement in statements:
        found = await session.execute(statement)
        mended += int(getattr(found, "rowcount", 0) or 0)
    await session.flush()
    return mended
