from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import AccusationRow, PurityRow, WitchHuntRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.folkways import AccusationOutcome, PurityState


async def mend_folkways_links(session: AsyncSession, epoch: int) -> int:
    vanished = select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)
    mended = 0
    for statement in (
        update(AccusationRow)
        .where(AccusationRow.outcome == AccusationOutcome.PENDING, AccusationRow.case_id.is_(None), AccusationRow.accused_node_id.in_(vanished))
        .values(outcome=AccusationOutcome.CLEARED, closed_epoch=epoch),
        update(WitchHuntRow).where(WitchHuntRow.ended_epoch.is_(None), WitchHuntRow.settlement_entity_id.in_(vanished)).values(ended_epoch=epoch),
        update(PurityRow)
        .where(PurityRow.state != PurityState.PURE, PurityRow.until_epoch.is_not(None), PurityRow.until_epoch < PurityRow.since_epoch)
        .values(until_epoch=PurityRow.since_epoch),
        delete(PurityRow).where(PurityRow.holder_node_id.in_(vanished), PurityRow.rank_id.is_(None)),
    ):
        result = await session.execute(statement)
        mended += max(0, getattr(result, "rowcount", 0) or 0)
    return mended
