from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.referendums import ReferendumRow
from aerona.domain.enums.referendums import ReferendumResult
from aerona.engine.referendums.book import franchise_at, realm_of_holder


async def open_votes(session: AsyncSession) -> list[ReferendumRow]:
    return list(await session.scalars(select(ReferendumRow).where(ReferendumRow.result == ReferendumResult.PENDING).order_by(ReferendumRow.id)))


async def law_of_vote(session: AsyncSession, row: ReferendumRow) -> str | None:
    holder = await session.get(EntityRow, row.holder_node_id)
    if holder is None:
        return None
    return (await franchise_at(session, await realm_of_holder(session, holder))).value


async def stray_franchises(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await open_votes(session):
        wanted = await law_of_vote(session, row)
        if wanted is not None and "franchise" not in (row.locked or []) and row.franchise.value != wanted:
            found.append(row.id)
    return found


async def align_franchise(session: AsyncSession, key: int) -> None:
    row = await session.get(ReferendumRow, key)
    wanted = await law_of_vote(session, row) if row is not None else None
    if row is not None and wanted is not None:
        row.franchise = type(row.franchise)(wanted)


async def aimless_votes(session: AsyncSession) -> list[int]:
    return [row.id for row in await open_votes(session) if row.target_node_id is None]


async def void_vote(session: AsyncSession, key: int) -> None:
    row = await session.get(ReferendumRow, key)
    if row is not None:
        row.result = ReferendumResult.VOID


async def early_votes(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(ReferendumRow).where(ReferendumRow.held_epoch.is_not(None)).order_by(ReferendumRow.id))
    return [row.id for row in rows if row.held_epoch is not None and row.held_epoch < row.called_epoch]


async def mend_held(session: AsyncSession, key: int) -> None:
    row = await session.get(ReferendumRow, key)
    if row is not None:
        row.held_epoch = row.called_epoch
