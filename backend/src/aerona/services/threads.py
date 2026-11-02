from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.lore import ThreadRow
from aerona.domain.enums.chronicle import ThreadStatus


async def list_threads(session: AsyncSession) -> list[ThreadRow]:
    order = (ThreadRow.status != ThreadStatus.OPEN, ThreadRow.id.desc())
    return list(await session.scalars(select(ThreadRow).order_by(*order)))
