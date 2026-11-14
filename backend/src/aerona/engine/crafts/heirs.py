from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.crafts import IncorporealRightRow
from aerona.db.write_guard import held
from aerona.domain.enums.crafts import RightAcquired


async def pass_rights(session: AsyncSession, holder_id: int, heir_id: int, epoch: int) -> int:
    passed = 0
    for row in list(await session.scalars(select(IncorporealRightRow).where(IncorporealRightRow.holder_node_id == holder_id).order_by(IncorporealRightRow.id))):
        if "holder_node_id" in row.locked or held(heir_id):
            continue
        row.holder_node_id = heir_id
        row.acquired = RightAcquired.INHERITED
        row.since_epoch = epoch
        passed += 1
    return passed
