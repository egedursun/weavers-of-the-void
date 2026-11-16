from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultDoctrineRow
from aerona.engine.sacred.places import church_of


async def doctrine_here(session: AsyncSession, being: EntityRow) -> CultDoctrineRow | None:
    town = await session.get(EntityRow, being.location_id) if being.location_id is not None else being
    church = await church_of(session, town or being)
    return await session.get(CultDoctrineRow, church.id) if church is not None else None
