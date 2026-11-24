from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.depth_positions import DEPTH_POSITIONS
from aerona.constants.units import PERCENT
from aerona.db.tables.couplings import DeepSealRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.geology import DeepPassageRow, RegionStratumRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.geology import DeepPassageState


async def cell_of(session: AsyncSession, region_id: int | None, stratum: object) -> RegionStratumRow | None:
    if region_id is None:
        return None
    return await session.scalar(select(RegionStratumRow).where(RegionStratumRow.region_entity_id == region_id, RegionStratumRow.stratum == stratum).limit(1))


async def misplaced_below(session: AsyncSession) -> list[int]:
    found: list[int] = []
    if not any(table == "entities" for table, _, _ in DEPTH_POSITIONS):
        return found
    for entity in await session.scalars(select(EntityRow).where(EntityRow.stratum.is_not(None)).order_by(EntityRow.id)):
        place = await session.get(EntityRow, entity.location_id) if entity.location_id is not None else None
        if place is None or place.entity_type is not EntityType.REGION or await cell_of(session, place.id, entity.stratum) is None:
            found.append(entity.id)
    return found


async def lift_to_surface(session: AsyncSession, key: int) -> None:
    entity = await session.get(EntityRow, key)
    if entity is not None:
        entity.stratum = None


async def wrong_passage_states(session: AsyncSession) -> list[int]:
    sealed = set(await session.scalars(select(DeepSealRow.passage_id).where(DeepSealRow.passage_id.is_not(None), DeepSealRow.broken_epoch.is_(None))))
    found: list[int] = []
    for row in await session.scalars(select(DeepPassageRow).order_by(DeepPassageRow.id)):
        if "state" in row.locked:
            continue
        digging = row.progress < PERCENT and not row.opened
        if (row.state is DeepPassageState.DIGGING) != digging or (row.state is DeepPassageState.SEALED) != (row.id in sealed):
            found.append(row.id)
    return found


async def settle_passage_state(session: AsyncSession, key: int) -> None:
    row = await session.get(DeepPassageRow, key)
    if row is None:
        return
    sealed = await session.scalar(select(DeepSealRow.id).where(DeepSealRow.passage_id == key, DeepSealRow.broken_epoch.is_(None)).limit(1))
    if sealed is not None:
        row.state = DeepPassageState.SEALED
    elif row.progress < PERCENT and not row.opened:
        row.state = DeepPassageState.DIGGING
    elif row.state in {DeepPassageState.DIGGING, DeepPassageState.SEALED}:
        row.state, row.opened, row.progress = DeepPassageState.OPEN, True, PERCENT


async def unbound_passages(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(DeepPassageRow).order_by(DeepPassageRow.id)):
        ends = ((row.first_region_entity_id, row.first_stratum), (row.second_region_entity_id, row.second_stratum))
        missing = False
        for region, stratum in ends:
            missing = missing or (stratum is not None and await cell_of(session, region, stratum) is None)
        wrong_place = row.place_entity_id is not None and not (
            row.first_region_entity_id == row.second_region_entity_id and None in (row.first_stratum, row.second_stratum)
        )
        if missing or wrong_place:
            found.append(row.id)
    return found


async def drop_passage(session: AsyncSession, key: int) -> None:
    row = await session.get(DeepPassageRow, key)
    if row is not None:
        await session.delete(row)
