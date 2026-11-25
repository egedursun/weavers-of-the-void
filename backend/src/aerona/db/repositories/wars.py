from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.war import WarStatus


async def wars_under_way(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(WarRow).where(WarRow.status != WarStatus.ENDED)) or 0)
