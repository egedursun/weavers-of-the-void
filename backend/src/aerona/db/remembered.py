from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.domain.enums.bond import BondKind, BondState


async def told_of(session: AsyncSession, tradition_id: int) -> int | None:
    found: int | None = await session.scalar(
        select(BondRow.target_node_id)
        .where(BondRow.source_node_id == tradition_id, BondRow.kind == BondKind.TELLS_OF, BondRow.state == BondState.ACTIVE)
        .order_by(BondRow.id)
        .limit(1)
    )
    return found
