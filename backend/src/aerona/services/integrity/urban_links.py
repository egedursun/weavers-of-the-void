from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import DistrictRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.urban import CrimeStanceRow, PayrollRow, RacketRow, TradingPostRow, TurfRow
from aerona.domain.enums.entity import EntityStatus


async def mend_urban_links(session: AsyncSession) -> int:
    vanished = select(EntityRow.id).where(EntityRow.status != EntityStatus.CANON)
    mended = 0
    statements = [
        delete(TurfRow).where(TurfRow.faction_entity_id.in_(vanished)),
        delete(RacketRow).where(RacketRow.faction_entity_id.in_(vanished)),
        delete(PayrollRow).where(PayrollRow.faction_entity_id.in_(vanished)),
        delete(CrimeStanceRow).where(CrimeStanceRow.faction_entity_id.in_(vanished)),
        delete(TradingPostRow).where(TradingPostRow.structure_entity_id.in_(vanished)),
    ]
    for statement in statements:
        found = await session.execute(statement)
        mended += int(getattr(found, "rowcount", 0) or 0)
    for profile, building, district in await session.execute(
        select(StructureProfileRow, EntityRow, DistrictRow)
        .join(EntityRow, EntityRow.id == StructureProfileRow.structure_entity_id)
        .join(DistrictRow, DistrictRow.id == StructureProfileRow.district_id)
    ):
        if building.location_id != district.settlement_entity_id:
            profile.district_id = None
            mended += 1
    await session.flush()
    return mended
