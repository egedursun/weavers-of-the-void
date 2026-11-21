from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.military import OccupationRow
from aerona.db.tables.occupation_regimes import CollaborationRow, OccupationMeasureRow, OccupationRegimeRow
from aerona.domain.enums.occupation_regimes import CollaborationFate, OccupationEnding
from aerona.engine.primitives.distance import RegionAtlas


async def open_regimes(session: AsyncSession) -> list[OccupationRegimeRow]:
    return list(await session.scalars(select(OccupationRegimeRow).where(OccupationRegimeRow.ended_epoch.is_(None)).order_by(OccupationRegimeRow.id)))


async def orphan_regimes(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for regime in await open_regimes(session):
        occupation = await session.get(OccupationRow, regime.region_entity_id)
        if occupation is None or occupation.occupier_entity_id != regime.occupier_entity_id:
            found.append(regime.id)
    return found


async def end_orphan(session: AsyncSession, key: int) -> None:
    regime = await session.get(OccupationRegimeRow, key)
    if regime is not None:
        regime.ended_epoch, regime.ending = regime.begun_epoch, OccupationEnding.WITHDRAWN


async def strangers(session: AsyncSession) -> list[int]:
    atlas = await RegionAtlas.load(session)
    found: list[int] = []
    query = select(CollaborationRow).where(CollaborationRow.fate == CollaborationFate.SERVING).order_by(CollaborationRow.id)
    for row in await session.scalars(query):
        regime = await session.get(OccupationRegimeRow, row.regime_id)
        if regime is None:
            continue
        near = {regime.region_entity_id, *atlas.neighbour_regions(regime.region_entity_id)}
        if atlas.top_region(row.collaborator_node_id) not in near:
            found.append(row.id)
    return found


async def end_stranger(session: AsyncSession, key: int) -> None:
    row = await session.get(CollaborationRow, key)
    regime = await session.get(OccupationRegimeRow, row.regime_id) if row is not None else None
    if row is not None:
        row.fate, row.ended_epoch = CollaborationFate.ENDED, row.begun_epoch if regime is None else max(row.begun_epoch, regime.begun_epoch)


async def mismatched_service(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(CollaborationRow).order_by(CollaborationRow.id))
    return [row.id for row in rows if (row.fate is CollaborationFate.SERVING) != (row.ended_epoch is None)]


async def mend_service(session: AsyncSession, key: int) -> None:
    row = await session.get(CollaborationRow, key)
    if row is not None:
        row.ended_epoch = None if row.fate is CollaborationFate.SERVING else max(row.begun_epoch, row.ended_epoch or row.begun_epoch)


async def loose_measures(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(OccupationMeasureRow).where(OccupationMeasureRow.ended_epoch.is_(None)).order_by(OccupationMeasureRow.id)):
        regime = await session.get(OccupationRegimeRow, row.regime_id)
        if regime is None or regime.ended_epoch is not None:
            found.append(row.id)
    return found


async def end_loose_measure(session: AsyncSession, key: int) -> None:
    row = await session.get(OccupationMeasureRow, key)
    regime = await session.get(OccupationRegimeRow, row.regime_id) if row is not None else None
    if row is not None:
        row.ended_epoch = max(row.epoch, regime.ended_epoch or row.epoch) if regime is not None else row.epoch


async def misplaced_measures(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(OccupationMeasureRow).order_by(OccupationMeasureRow.id)):
        regime = await session.get(OccupationRegimeRow, row.regime_id)
        if regime is not None and regime.region_entity_id != row.region_entity_id:
            found.append(row.id)
    return found


async def place_measure(session: AsyncSession, key: int) -> None:
    row = await session.get(OccupationMeasureRow, key)
    regime = await session.get(OccupationRegimeRow, row.regime_id) if row is not None else None
    if row is not None and regime is not None:
        row.region_entity_id = regime.region_entity_id
