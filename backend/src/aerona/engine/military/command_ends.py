from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.military import ArmyOfficerRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held


async def lay_down_command(session: AsyncSession, mortal_id: int, epoch: int) -> int:
    armies = list(
        await session.scalars(select(ArmyRow).where(ArmyRow.commander_entity_id == mortal_id, ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id))
    )
    for army in armies:
        if not held(army.entity_id):
            army.commander_entity_id = None
    for officer in await session.scalars(
        select(ArmyOfficerRow).where(ArmyOfficerRow.mortal_entity_id == mortal_id, ArmyOfficerRow.until_epoch.is_(None)).order_by(ArmyOfficerRow.id)
    ):
        if not held(officer.army_entity_id):
            officer.until_epoch = epoch
    return len(armies)
