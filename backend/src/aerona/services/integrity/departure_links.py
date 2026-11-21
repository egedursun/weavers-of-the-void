from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.departures import DepartureRow
from aerona.db.tables.polity import OfficeRow


async def departures(session: AsyncSession) -> list[DepartureRow]:
    return list(await session.scalars(select(DepartureRow).order_by(DepartureRow.id)))


async def handed_to_self(session: AsyncSession) -> list[int]:
    return [row.id for row in await departures(session) if row.in_favour_of_node_id is not None and row.in_favour_of_node_id == row.holder_node_id]


async def clear_successor(session: AsyncSession, key: int) -> None:
    row = await session.get(DepartureRow, key)
    if row is not None:
        row.in_favour_of_node_id = None


async def stray_offices(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await departures(session):
        office = await session.get(OfficeRow, row.office_id) if row.office_id is not None else None
        if office is not None and (office.polity_entity_id != row.polity_entity_id or office.kind is not row.office_kind):
            found.append(row.id)
    return found


async def align_office(session: AsyncSession, key: int) -> None:
    row = await session.get(DepartureRow, key)
    office = await session.get(OfficeRow, row.office_id) if row is not None and row.office_id is not None else None
    if row is not None and office is not None:
        row.polity_entity_id, row.office_kind = office.polity_entity_id, office.kind


async def early_returns(session: AsyncSession) -> list[int]:
    return [row.id for row in await departures(session) if row.returned_epoch is not None and row.returned_epoch < row.epoch]


async def mend_return(session: AsyncSession, key: int) -> None:
    row = await session.get(DepartureRow, key)
    if row is not None:
        row.returned_epoch = row.epoch
