from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityFlagRow
from aerona.domain.enums.entity import EntityFlag

KEPT_NAME_FLAGS = (EntityFlag.NAME_FROM_LANGUAGE, EntityFlag.FIXED_NAME, EntityFlag.NAMELESS)


async def keeps_name(session: AsyncSession, entity_id: int) -> bool:
    found = await session.scalar(select(EntityFlagRow.entity_id).where(EntityFlagRow.entity_id == entity_id, EntityFlagRow.flag.in_(KEPT_NAME_FLAGS)).limit(1))
    return found is not None
