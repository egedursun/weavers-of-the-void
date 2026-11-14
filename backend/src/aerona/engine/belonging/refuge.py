from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.belonging import SanctuaryRow
from aerona.domain.enums.belonging import SanctuaryState

OPEN_STATES = (SanctuaryState.SHELTERED, SanctuaryState.NEGOTIATING, SanctuaryState.BESIEGED)


async def refuge_of(session: AsyncSession, mortal_id: int) -> SanctuaryRow | None:
    found: SanctuaryRow | None = await session.scalar(
        select(SanctuaryRow).where(SanctuaryRow.fugitive_entity_id == mortal_id, SanctuaryRow.state.in_(OPEN_STATES)).order_by(SanctuaryRow.id).limit(1)
    )
    return found


async def sheltered(session: AsyncSession, mortal_id: int) -> bool:
    return await refuge_of(session, mortal_id) is not None
