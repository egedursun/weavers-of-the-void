from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.labour import ACT_OUTPUT_LOSS_PCT
from aerona.constants.units import PERCENT
from aerona.db.tables.demography import LabourRow
from aerona.db.tables.labour import LabourDisputeRow
from aerona.domain.enums.demography import Job
from aerona.domain.enums.labour import DisputeOutcome


async def stoppage(session: AsyncSession, loss_pct: int, community_id: int) -> dict[Job, float]:
    query = select(LabourDisputeRow).where(LabourDisputeRow.settlement_entity_id == community_id, LabourDisputeRow.outcome == DisputeOutcome.ONGOING)
    disputes = list(await session.scalars(query.order_by(LabourDisputeRow.id)))
    if not disputes:
        return {}
    workers = {row.job: row.workers for row in await session.scalars(select(LabourRow).where(LabourRow.community_entity_id == community_id))}
    lost: dict[Job, float] = {}
    for dispute in disputes:
        total = workers.get(dispute.trade, 0)
        if not total:
            continue
        share = min(1.0, dispute.workers_out / total) * ACT_OUTPUT_LOSS_PCT[dispute.act] / PERCENT * loss_pct / PERCENT
        lost[dispute.trade] = min(1.0, lost.get(dispute.trade, 0.0) + share)
    return {trade: 1.0 - share for trade, share in sorted(lost.items(), key=lambda item: item[0].value)}
