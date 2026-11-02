from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.lifecycle.aging import medicine_regions, raise_lifespan_to_death_age
from aerona.engine.primitives.distance import RegionAtlas
from aerona.rules.registry import Rules


async def raise_lifespans(session: AsyncSession, rules: Rules) -> int:
    atlas = await RegionAtlas.load(session)
    medicine = await medicine_regions(session, atlas)
    statement = select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.DEAD).order_by(EntityRow.id)
    raised = 0
    for mortal in await session.scalars(statement):
        if await raise_lifespan_to_death_age(session, rules, mortal, atlas, medicine):
            raised += 1
    await session.flush()
    return raised
