from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.agrarian import ReconstructionRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus


async def rebuilds_of_the_ended(session: AsyncSession) -> list[int]:
    rows = await session.execute(
        select(ReconstructionRow.id, ReconstructionRow.settlement_entity_id)
        .join(EntityRow, EntityRow.id == ReconstructionRow.settlement_entity_id)
        .where(ReconstructionRow.finished_epoch.is_(None), EntityRow.status != EntityStatus.CANON)
        .order_by(ReconstructionRow.id)
    )
    return [row_id for row_id, town_id in rows if not held(town_id)]


async def close_rebuild(session: AsyncSession, row_id: int) -> None:
    row = await session.get(ReconstructionRow, row_id)
    if row is not None and row.finished_epoch is None:
        row.finished_epoch = await session.scalar(select(CosmosRow.epoch).limit(1)) or 0
