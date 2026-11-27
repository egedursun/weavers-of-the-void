from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import ENDED_STATUSES


async def still_standing(session: AsyncSession, node_id: int | None) -> bool:
    if node_id is None:
        return False
    entity = await session.get(EntityRow, node_id)
    return entity is None or entity.status not in ENDED_STATUSES


def ended_ids() -> Select[int]:
    return select(EntityRow.id).where(EntityRow.status.in_(sorted(ENDED_STATUSES)))
