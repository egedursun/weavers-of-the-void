from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.restoration import RestorationRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.restoration import OPEN_STAGES, RestorationStage
from aerona.engine.primitives.queries import active_bonds, connect


async def restorations(session: AsyncSession) -> list[RestorationRow]:
    return list(await session.scalars(select(RestorationRow).order_by(RestorationRow.id)))


async def living_fallen(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await restorations(session):
        fallen = await session.get(EntityRow, row.fallen_polity_id)
        if row.stage in OPEN_STAGES and (fallen is None or fallen.status is EntityStatus.CANON):
            found.append(row.id)
    return found


async def end_living_fallen(session: AsyncSession, key: int) -> None:
    row = await session.get(RestorationRow, key)
    if row is not None:
        row.stage, row.ended_epoch = RestorationStage.FAILED, row.begun_epoch


async def unlinked_restored(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await restorations(session):
        if row.stage is not RestorationStage.RESTORED:
            continue
        links = await active_bonds(session, [BondKind.DESCENDS_FROM], [row.restored_polity_id]) if row.restored_polity_id is not None else []
        if not any(bond.target_node_id == row.fallen_polity_id for bond in links):
            found.append(row.id)
    return found


async def link_restored(session: AsyncSession, key: int) -> None:
    row = await session.get(RestorationRow, key)
    if row is None:
        return
    if row.restored_polity_id is None:
        row.stage = RestorationStage.FAILED
        return
    await connect(
        session, row.restored_polity_id, row.fallen_polity_id, BondKind.DESCENDS_FROM, row.ended_epoch or row.begun_epoch, description="restored the old realm"
    )


async def mismatched_ends(session: AsyncSession) -> list[int]:
    return [row.id for row in await restorations(session) if (row.stage in OPEN_STAGES) != (row.ended_epoch is None)]


async def mend_end(session: AsyncSession, key: int) -> None:
    row = await session.get(RestorationRow, key)
    if row is not None:
        row.ended_epoch = None if row.stage in OPEN_STAGES else max(row.begun_epoch, row.ended_epoch or row.begun_epoch)
