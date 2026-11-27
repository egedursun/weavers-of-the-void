from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.node import NodeBirthRow
from aerona.db.write_guard import held
from aerona.domain.models.calendar import epoch_start_year


def fitted_year(year: int | None, epoch: int, years: int, told: int | None, born: int | None) -> int:
    start = epoch_start_year(epoch, years)
    if told is not None and start <= told < start + years:
        chosen = told
    elif year is not None and start <= year < start + years:
        chosen = year
    elif year is not None and 0 <= year < years:
        chosen = start + year
    else:
        chosen = start
    if born is not None and born < start + years:
        chosen = max(chosen, born)
    return chosen


async def injury_dates(session: AsyncSession) -> list[tuple[int, int, int | None, int, int | None, int | None]]:
    statement = (
        select(InjuryRow.id, InjuryRow.bearer_node_id, InjuryRow.year, InjuryRow.epoch, IncidentRow.year, NodeBirthRow.year)
        .outerjoin(IncidentRow, IncidentRow.id == InjuryRow.incident_id)
        .outerjoin(NodeBirthRow, NodeBirthRow.node_id == InjuryRow.bearer_node_id)
        .order_by(InjuryRow.id)
    )
    return [(int(row[0]), int(row[1]), row[2], int(row[3]), row[4], row[5]) for row in await session.execute(statement)]


async def injuries_out_of_their_time(session: AsyncSession) -> list[int]:
    years = (await CosmosRepository(session).rules()).time.years_per_epoch
    return [
        injury_id
        for injury_id, bearer, year, epoch, told, born in await injury_dates(session)
        if not held(bearer) and year != fitted_year(year, epoch, years, told, born)
    ]


async def date_injury_in_its_time(session: AsyncSession, injury_id: int) -> None:
    row = await session.get(InjuryRow, injury_id)
    if row is None:
        return
    years = (await CosmosRepository(session).rules()).time.years_per_epoch
    told = await session.scalar(select(IncidentRow.year).where(IncidentRow.id == row.incident_id)) if row.incident_id is not None else None
    born = await session.scalar(select(NodeBirthRow.year).where(NodeBirthRow.node_id == row.bearer_node_id))
    row.year = fitted_year(row.year, row.epoch, years, told, born)
