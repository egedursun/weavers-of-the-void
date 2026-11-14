from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.ages import AgeEchoRow, ArcRow, SetupRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.ages import ArcOutcome, PayoffKind
from aerona.domain.enums.entity import EntityStatus


async def mend_ages_links(session: AsyncSession, epoch: int) -> int:
    vanished = select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)
    mended = 0
    for statement in (
        update(ArcRow).where(ArcRow.outcome == ArcOutcome.OPEN, ArcRow.subject_node_id.in_(vanished)).values(outcome=ArcOutcome.FAILED, ended_epoch=epoch),
        update(SetupRow).where(SetupRow.payoff == PayoffKind.OPEN, SetupRow.subject_node_id.in_(vanished)).values(payoff=PayoffKind.LAPSED, paid_epoch=epoch),
        update(AgeEchoRow).where(AgeEchoRow.echo_node_id.in_(vanished)).values(echo_node_id=None),
    ):
        result = await session.execute(statement)
        mended += max(0, getattr(result, "rowcount", 0) or 0)
    return mended
