from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.crafts import AssistiveAidRow
from aerona.domain.enums.crafts import AssistiveAid


async def aid_quality(session: AsyncSession, holder_id: int, kind: AssistiveAid) -> int:
    row = await session.get(AssistiveAidRow, (holder_id, kind))
    return row.quality if row is not None else 0
