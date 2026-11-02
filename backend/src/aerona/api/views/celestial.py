from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.schemas.cosmos import WorldCounts
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType

LIVING_TYPES = (EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.MORTAL, EntityType.SPECIES, EntityType.CULT, EntityType.FACTION)


async def count_types(session: AsyncSession, world_id: int, types: tuple[EntityType, ...]) -> int:
    statement = select(func.count()).select_from(EntityRow).where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON)
    return int(await session.scalar(statement.where(EntityRow.entity_type.in_(types))) or 0)


async def population(session: AsyncSession, world_id: int) -> int:
    peoples = await session.scalars(
        select(EntityRow).where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type == EntityType.PEOPLE)
    )
    return sum(int(getattr(people.stats, "population", 0) or 0) for people in peoples)


async def world_counts(session: AsyncSession, world_id: int) -> WorldCounts:
    return WorldCounts(
        regions=await count_types(session, world_id, (EntityType.REGION,)),
        peoples=await count_types(session, world_id, (EntityType.PEOPLE,)),
        settlements=await count_types(session, world_id, (EntityType.SETTLEMENT,)),
        living=await count_types(session, world_id, LIVING_TYPES),
        population=await population(session, world_id),
    )
