from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.ages import AgeEchoRow, ArcRow, SetupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.record_keepers import RecordKeeperRow
from aerona.domain.enums.ages import ArcOutcome, PayoffKind
from aerona.domain.enums.entity import EntityStatus, EntityType


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


async def keepers_not_mortal(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(RecordKeeperRow).where(RecordKeeperRow.keeper_entity_id.is_not(None)).order_by(RecordKeeperRow.id)):
        keeper = await session.get(EntityRow, row.keeper_entity_id)
        if keeper is None or keeper.entity_type is not EntityType.MORTAL:
            found.append(row.id)
    return found


async def free_keeper_seat(session: AsyncSession, key: int) -> None:
    row = await session.get(RecordKeeperRow, key)
    if row is not None:
        row.keeper_entity_id = None
        row.locked = [field for field in row.locked or [] if field != "keeper_entity_id"]
