from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.culture import HolderLevelRow
from aerona.domain.enums.mind import ValueAxis
from aerona.engine.mind.book import values_for


async def liberty_of(session: AsyncSession, node_id: int) -> int:
    values = await values_for(session, node_id)
    return -(values.get(ValueAxis.HIERARCHY, 0) + values.get(ValueAxis.LAW, 0)) // 2


async def best_level(session: AsyncSession, holder_id: int) -> int:
    return int(await session.scalar(select(func.max(HolderLevelRow.level)).where(HolderLevelRow.holder_entity_id == holder_id)) or 0)
