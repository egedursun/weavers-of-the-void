from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType

DWELLING_TYPES = frozenset({EntityType.REGION, EntityType.PLACE, EntityType.SETTLEMENT})
CHAIN_HOPS = 8


async def mortals_in_no_place(session: AsyncSession) -> list[int]:
    where = aliased(EntityRow)
    rows = await session.scalars(
        select(EntityRow.id)
        .join(where, where.id == EntityRow.location_id)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, where.entity_type.not_in(list(DWELLING_TYPES)))
        .order_by(EntityRow.id)
    )
    return list(rows)


async def dwelling_of(session: AsyncSession, node_id: int | None) -> int | None:
    for _ in range(CHAIN_HOPS):
        found = await session.get(EntityRow, node_id) if node_id is not None else None
        if found is None:
            return None
        if found.entity_type in DWELLING_TYPES:
            return found.id
        node_id = found.location_id
    return None


async def settle_in_place(session: AsyncSession, key: int) -> None:
    mortal = await session.get(EntityRow, key)
    if mortal is None:
        return
    mortal.location_id = await dwelling_of(session, mortal.location_id)
