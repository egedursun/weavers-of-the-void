from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.departures import DepartureRow
from aerona.db.tables.node import NodeBirthRow
from aerona.db.write_guard import held
from aerona.domain.models.calendar import epoch_end_year


def longest_tenure(epoch: int, years: int, came: int | None) -> int | None:
    return None if came is None else max(0, epoch_end_year(epoch, years) - came)


async def tenures_beyond_presence(session: AsyncSession) -> list[int]:
    years = (await CosmosRepository(session).rules()).time.years_per_epoch
    rows = await session.execute(
        select(DepartureRow.id, DepartureRow.holder_node_id, DepartureRow.epoch, DepartureRow.years_held, DepartureRow.locked, NodeBirthRow.year)
        .join(NodeBirthRow, NodeBirthRow.node_id == DepartureRow.holder_node_id)
        .order_by(DepartureRow.id)
    )
    found: list[int] = []
    for row_id, holder, epoch, held_for, locked, came in rows:
        bound = longest_tenure(epoch, years, came)
        if bound is not None and held_for > bound and "years_held" not in (locked or []) and not held(holder):
            found.append(int(row_id))
    return found


async def bound_tenure(session: AsyncSession, row_id: int) -> None:
    row = await session.get(DepartureRow, row_id)
    if row is None:
        return
    came = await session.scalar(select(NodeBirthRow.year).where(NodeBirthRow.node_id == row.holder_node_id))
    bound = longest_tenure(row.epoch, (await CosmosRepository(session).rules()).time.years_per_epoch, came)
    if bound is not None and row.years_held > bound:
        row.years_held = bound
