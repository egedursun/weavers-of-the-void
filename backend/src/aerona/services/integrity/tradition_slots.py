from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.lore import slot_fit
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityOrigin


async def misfit_traditions(session: AsyncSession) -> list[int]:
    rows = await session.execute(
        select(TraditionProfileRow)
        .join(EntityRow, EntityRow.id == TraditionProfileRow.tradition_entity_id)
        .where(EntityRow.origin == EntityOrigin.ENGINE)
        .order_by(TraditionProfileRow.tradition_entity_id)
    )
    return [
        row.tradition_entity_id
        for (row,) in rows
        if "calendar_slot" not in row.locked and not held(row.tradition_entity_id) and row.calendar_slot is not slot_fit(row.kind, row.stage)
    ]


async def refit_tradition(session: AsyncSession, tradition_id: int) -> None:
    row = await session.get(TraditionProfileRow, tradition_id)
    if row is not None and "calendar_slot" not in row.locked:
        row.calendar_slot = slot_fit(row.kind, row.stage)
