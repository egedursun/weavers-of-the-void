from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.evolution import PlagueResponseRow
from aerona.domain.enums.evolution import PlagueResponse


async def closed_borders(session: AsyncSession, epoch: int) -> set[int]:
    return set(
        await session.scalars(
            select(PlagueResponseRow.community_entity_id).where(
                PlagueResponseRow.response == PlagueResponse.CLOSE_BORDERS,
                or_(PlagueResponseRow.until_epoch.is_(None), PlagueResponseRow.until_epoch >= epoch),
            )
        )
    )
