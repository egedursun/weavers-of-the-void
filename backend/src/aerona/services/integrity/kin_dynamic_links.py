from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kin_dynamics import ElderSwayRow, KinDynamicRow, KinFavourRow, KinRivalryRow
from aerona.domain.enums.entity import EntityStatus


async def unscoped_dynamics(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(KinDynamicRow).order_by(KinDynamicRow.id))
    return [row.id for row in rows if (row.household_id is None) == (row.house_entity_id is None)]


async def scope_dynamic(session: AsyncSession, key: int) -> None:
    row = await session.get(KinDynamicRow, key)
    if row is None:
        return
    if row.house_entity_id is not None:
        row.household_id = None
    else:
        await session.delete(row)


async def self_ties(session: AsyncSession) -> list[int]:
    favours = await session.scalars(select(KinFavourRow).order_by(KinFavourRow.id))
    return [row.id for row in favours if row.parent_node_id == row.child_node_id]


async def drop_self_favour(session: AsyncSession, key: int) -> None:
    row = await session.get(KinFavourRow, key)
    if row is not None:
        await session.delete(row)


async def lopsided_rivalries(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(KinRivalryRow).order_by(KinRivalryRow.id))
    return [row.id for row in rows if row.first_node_id >= row.second_node_id]


async def order_rivalry(session: AsyncSession, key: int) -> None:
    row = await session.get(KinRivalryRow, key)
    if row is None:
        return
    if row.first_node_id == row.second_node_id:
        await session.delete(row)
    else:
        row.first_node_id, row.second_node_id = sorted((row.first_node_id, row.second_node_id))


async def dead_elders(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(ElderSwayRow).where(ElderSwayRow.ended_epoch.is_(None)).order_by(ElderSwayRow.id)):
        elder = await session.get(EntityRow, row.elder_node_id)
        if elder is not None and elder.status is not EntityStatus.CANON:
            found.append(row.id)
    return found


async def end_elder(session: AsyncSession, key: int) -> None:
    row = await session.get(ElderSwayRow, key)
    if row is not None:
        row.ended_epoch = row.since_epoch
