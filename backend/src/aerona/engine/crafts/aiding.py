from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.crafts import AssistiveAidRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.crafts import AssistiveAid
from aerona.domain.enums.entity import EntityStatus


async def aid_quality(session: AsyncSession, holder_id: int, kind: AssistiveAid) -> int:
    row = await session.get(AssistiveAidRow, (holder_id, kind))
    return row.quality if row is not None else 0


async def lens_in(session: AsyncSession, town_id: int) -> bool:
    here = select(EntityRow.id).where(EntityRow.location_id == town_id, EntityRow.status == EntityStatus.CANON)
    found = await session.scalar(
        select(AssistiveAidRow.holder_node_id).where(AssistiveAidRow.kind == AssistiveAid.MICROSCOPE, AssistiveAidRow.holder_node_id.in_(here)).limit(1)
    )
    return found is not None
