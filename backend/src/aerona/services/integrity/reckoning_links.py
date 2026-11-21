from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.reckoning import ReckoningCaseRow, ReckoningMeasureRow, ReckoningRow


async def known_incidents(session: AsyncSession, ids: list[int]) -> set[int]:
    return set(await session.scalars(select(IncidentRow.id).where(IncidentRow.id.in_(ids)))) if ids else set()


async def unrecorded_acts(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for case in await session.scalars(select(ReckoningCaseRow).order_by(ReckoningCaseRow.id)):
        acts = list(case.incident_ids or [])
        if acts and await known_incidents(session, acts) != set(acts):
            found.append(case.id)
    return found


async def keep_recorded(session: AsyncSession, key: int) -> None:
    case = await session.get(ReckoningCaseRow, key)
    if case is not None:
        known = await known_incidents(session, list(case.incident_ids or []))
        case.incident_ids = [act for act in case.incident_ids or [] if act in known]


async def reckonings_before_the_fall(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(ReckoningRow).order_by(ReckoningRow.id))
    return [row.id for row in rows if row.fallen_epoch > row.opened_epoch]


async def mend_fall(session: AsyncSession, key: int) -> None:
    row = await session.get(ReckoningRow, key)
    if row is not None:
        row.fallen_epoch = row.opened_epoch


async def stray_measures(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for measure in await session.scalars(select(ReckoningMeasureRow).order_by(ReckoningMeasureRow.id)):
        row = await session.get(ReckoningRow, measure.reckoning_id)
        if row is not None and measure.polity_entity_id != row.polity_entity_id:
            found.append(measure.id)
    return found


async def align_measure(session: AsyncSession, key: int) -> None:
    measure = await session.get(ReckoningMeasureRow, key)
    row = await session.get(ReckoningRow, measure.reckoning_id) if measure is not None else None
    if measure is not None and row is not None:
        measure.polity_entity_id = row.polity_entity_id
