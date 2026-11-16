from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.equipment import EquipmentModelRow, EquipmentStoreRow
from aerona.domain.enums.powers import PowerDeviceEffect


async def devices_of(session: AsyncSession, holder_ids: list[int]) -> list[PowerDeviceEffect]:
    rows = await session.scalars(
        select(EquipmentModelRow.power_effect)
        .join(EquipmentStoreRow, EquipmentStoreRow.model_id == EquipmentModelRow.id)
        .where(EquipmentStoreRow.holder_node_id.in_(holder_ids), EquipmentStoreRow.count > 0, EquipmentModelRow.power_effect.is_not(None))
    )
    return [row for row in rows if row is not None]
