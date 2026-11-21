from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.grave_goods import GraveGoodsRow
from aerona.domain.enums.bond import BondKind
from aerona.engine.primitives.queries import active_bonds


async def kept_items(session: AsyncSession, row: GraveGoodsRow) -> list[int]:
    held_by_dead = {bond.target_node_id for bond in await active_bonds(session, [BondKind.OWNS], sources=[row.dead_entity_id])}
    return [item for item in row.items or [] if item in held_by_dead]


async def loose_grave_goods(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(GraveGoodsRow).order_by(GraveGoodsRow.id))
    return [row.id for row in rows if await kept_items(session, row) != list(row.items or [])]


async def gather_grave_goods(session: AsyncSession, key: int) -> None:
    row = await session.get(GraveGoodsRow, key)
    if row is not None:
        row.items = await kept_items(session, row)
