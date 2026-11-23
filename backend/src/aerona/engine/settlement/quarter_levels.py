from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.settlement import DistrictRow
from aerona.domain.enums.settlement import DistrictKind


async def quarter_levels(session: AsyncSession, kind: DistrictKind) -> dict[int, int]:
    statement = (
        select(DistrictRow.settlement_entity_id, func.sum(DistrictRow.level))
        .where(DistrictRow.kind == kind, DistrictRow.condition > 0)
        .group_by(DistrictRow.settlement_entity_id)
    )
    return {int(town): int(levels) for town, levels in await session.execute(statement)}
