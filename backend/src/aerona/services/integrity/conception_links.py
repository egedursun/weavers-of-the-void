from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.divine_conceptions import GodReadingRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow


async def is_god(session: AsyncSession, node_id: int) -> bool:
    return await session.get(SonRow, node_id) is not None or await session.get(ForeignGodRow, node_id) is not None


async def false_gods(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(GodReadingRow).order_by(GodReadingRow.cult_entity_id, GodReadingRow.god_node_id))
    return sorted({row.god_node_id for row in rows if not await is_god(session, row.god_node_id)})


async def strike_false_god(session: AsyncSession, key: int) -> None:
    for row in list(await session.scalars(select(GodReadingRow).where(GodReadingRow.god_node_id == key).order_by(GodReadingRow.cult_entity_id))):
        await session.delete(row)
