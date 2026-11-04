from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.mortal import MortalEquipmentRow, MortalProfileRow


async def profile_of(session: AsyncSession, mortal_id: int) -> MortalProfileRow | None:
    return await session.get(MortalProfileRow, mortal_id)


async def ensure_profile(session: AsyncSession, mortal_id: int, epoch: int) -> tuple[MortalProfileRow, bool]:
    row = await session.get(MortalProfileRow, mortal_id)
    if row is not None:
        return row, False
    row = MortalProfileRow(entity_id=mortal_id, updated_epoch=max(0, epoch), locked=[])
    session.add(row)
    await session.flush()
    return row, True


async def profiles_for(session: AsyncSession, mortal_ids: list[int]) -> dict[int, MortalProfileRow]:
    if not mortal_ids:
        return {}
    rows = await session.scalars(select(MortalProfileRow).where(MortalProfileRow.entity_id.in_(mortal_ids)))
    return {row.entity_id: row for row in rows}


async def ensure_equipment(session: AsyncSession, mortal_id: int) -> MortalEquipmentRow:
    row = await session.get(MortalEquipmentRow, mortal_id)
    if row is None:
        row = MortalEquipmentRow(entity_id=mortal_id, locked=[])
        session.add(row)
        await session.flush()
    return row


def is_held(row: MortalProfileRow | MortalEquipmentRow | None, field: str) -> bool:
    return row is not None and field in (row.locked or [])
