from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.fertility_means import FertilityMeansRow, FertilityUseRow
from aerona.engine.fertility_means.factor import conceives


async def barren_means(session: AsyncSession) -> list[int]:
    peoples = sorted(set(await session.scalars(select(FertilityMeansRow.people_entity_id))))
    return [people for people in peoples if not await conceives(session, people)]


async def strike_barren_means(session: AsyncSession, key: int) -> None:
    for row in list(await session.scalars(select(FertilityMeansRow).where(FertilityMeansRow.people_entity_id == key).order_by(FertilityMeansRow.means))):
        await session.delete(row)


async def unknown_uses(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(FertilityUseRow).order_by(FertilityUseRow.id))
    return [row.id for row in rows if await session.get(FertilityMeansRow, (row.people_entity_id, row.means)) is None]


async def strike_unknown_use(session: AsyncSession, key: int) -> None:
    row = await session.get(FertilityUseRow, key)
    if row is not None:
        await session.delete(row)
