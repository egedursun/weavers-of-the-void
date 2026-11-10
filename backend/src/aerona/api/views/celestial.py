from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.schemas.cosmos import WorldCounts
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType

LIVING_TYPES = (EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.MORTAL, EntityType.SPECIES, EntityType.CULT, EntityType.FACTION)
COUNTED_TYPES = (EntityType.REGION, EntityType.PEOPLE, EntityType.SETTLEMENT, *LIVING_TYPES)


async def count_types(session: AsyncSession, world_id: int, types: tuple[EntityType, ...]) -> int:
    statement = select(func.count()).select_from(EntityRow).where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON)
    return int(await session.scalar(statement.where(EntityRow.entity_type.in_(types))) or 0)


async def population(session: AsyncSession, world_id: int) -> int:
    peoples = await session.scalars(
        select(EntityRow).where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type == EntityType.PEOPLE)
    )
    return sum(int(getattr(people.stats, "population", 0) or 0) for people in peoples)


async def worlds_counts(session: AsyncSession, world_ids: Iterable[int]) -> dict[int, WorldCounts]:
    wanted = set(world_ids)
    if not wanted:
        return {}
    statement = (
        select(EntityRow.world_id, EntityRow.entity_type, func.count())
        .where(EntityRow.world_id.in_(wanted), EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(COUNTED_TYPES))
        .group_by(EntityRow.world_id, EntityRow.entity_type)
    )
    tally: dict[int, dict[EntityType, int]] = {world_id: {} for world_id in wanted}
    for world_id, entity_type, count in await session.execute(statement):
        tally[world_id][entity_type] = int(count)
    peoples = await session.scalars(
        select(EntityRow).where(EntityRow.world_id.in_(wanted), EntityRow.status == EntityStatus.CANON, EntityRow.entity_type == EntityType.PEOPLE)
    )
    population: dict[int, int] = {world_id: 0 for world_id in wanted}
    for people in peoples:
        population[people.world_id] += int(getattr(people.stats, "population", 0) or 0)
    return {
        world_id: WorldCounts(
            regions=tally[world_id].get(EntityType.REGION, 0),
            peoples=tally[world_id].get(EntityType.PEOPLE, 0),
            settlements=tally[world_id].get(EntityType.SETTLEMENT, 0),
            living=sum(tally[world_id].get(kind, 0) for kind in LIVING_TYPES),
            population=population[world_id],
        )
        for world_id in wanted
    }


async def world_counts(session: AsyncSession, world_id: int) -> WorldCounts:
    return (await worlds_counts(session, [world_id]))[world_id]
