from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cycles import CircuitRow


async def circuit_stops(session: AsyncSession) -> list[int]:
    return [stop for stops in await session.scalars(select(CircuitRow.stops).order_by(CircuitRow.id)) for stop in stops]


async def circuit_partners(session: AsyncSession, stop_id: int | None) -> set[int]:
    if stop_id is None:
        return set()
    partners: set[int] = set()
    for stops in await session.scalars(select(CircuitRow.stops).order_by(CircuitRow.id)):
        if stop_id in stops:
            partners.update(stop for stop in stops if stop != stop_id)
    return partners
