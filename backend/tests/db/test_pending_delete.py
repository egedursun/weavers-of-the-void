from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityFlagRow
from aerona.domain.enums.entity import EntityFlag, EntityType
from tests.db.factories import make_entity


async def test_deleting_a_row_never_stored_simply_drops_it(session: AsyncSession, world_id: int) -> None:
    region = await make_entity(session, "Ashvale", EntityType.REGION, world_id=world_id)
    pending = EntityFlagRow(entity_id=region.id, flag=EntityFlag.PROTECTED, epoch=1)
    session.add(pending)
    await session.delete(pending)
    await session.flush()
    assert await session.scalar(select(EntityFlagRow).where(EntityFlagRow.entity_id == region.id)) is None
    stored = EntityFlagRow(entity_id=region.id, flag=EntityFlag.PROTECTED, epoch=1)
    session.add(stored)
    await session.flush()
    await session.delete(stored)
    await session.flush()
    assert await session.scalar(select(EntityFlagRow).where(EntityFlagRow.entity_id == region.id)) is None
