from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.operations import ShipCrewRow
from aerona.db.tables.polity import OathRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.war import CaptiveStatus
from aerona.engine.operations.crews import present_sections, station_fits


async def misplaced(session: AsyncSession, vessel_id: int) -> list[ShipCrewRow]:
    row = await session.get(VesselProfileRow, vessel_id)
    if row is None:
        return []
    sections = await present_sections(session, vessel_id, row)
    crews = await session.scalars(select(ShipCrewRow).where(ShipCrewRow.vessel_entity_id == vessel_id).order_by(ShipCrewRow.station))
    return [crew for crew in crews if not station_fits(crew.station, sections, row.frame)]


async def misplaced_crews(session: AsyncSession) -> list[int]:
    vessels = await session.scalars(select(ShipCrewRow.vessel_entity_id).distinct().order_by(ShipCrewRow.vessel_entity_id))
    return [vessel_id for vessel_id in list(vessels) if await misplaced(session, vessel_id)]


async def strike_misplaced_crew(session: AsyncSession, key: int) -> None:
    for crew in await misplaced(session, key):
        await session.delete(crew)


async def oathless_paroles(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(CaptiveRow).where(CaptiveRow.status == CaptiveStatus.PAROLED).order_by(CaptiveRow.id)):
        if row.oath_id is None or await session.get(OathRow, row.oath_id) is None:
            found.append(row.id)
    return found


async def release_oathless(session: AsyncSession, key: int) -> None:
    row = await session.get(CaptiveRow, key)
    if row is not None and row.status is CaptiveStatus.PAROLED:
        row.status = CaptiveStatus.RELEASED


async def unwed_joiners(session: AsyncSession) -> list[int]:
    statement = select(CaptiveRow.id).where(CaptiveRow.status == CaptiveStatus.MARRIED_IN, CaptiveRow.married_entity_id.is_(None))
    return list(await session.scalars(statement.order_by(CaptiveRow.id)))


async def release_unwed(session: AsyncSession, key: int) -> None:
    row = await session.get(CaptiveRow, key)
    if row is not None and row.status is CaptiveStatus.MARRIED_IN:
        row.status = CaptiveStatus.RELEASED
