from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.creature_groups import CreatureGroupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mass_weapons import WarRemnantRow
from aerona.db.tables.protected_nature import ProtectedAreaRow
from aerona.db.tables.sea_waves import SeaWaveCoastRow, SeaWaveRow


async def region_remnants(session: AsyncSession, world_id: int) -> dict[int, WarRemnantRow]:
    query = (
        select(WarRemnantRow)
        .join(EntityRow, EntityRow.id == WarRemnantRow.region_entity_id)
        .where(EntityRow.world_id == world_id, WarRemnantRow.density > 0)
        .order_by(WarRemnantRow.id)
    )
    densest: dict[int, WarRemnantRow] = {}
    for row in await session.scalars(query):
        region = row.region_entity_id
        if region is not None and (region not in densest or row.density > densest[region].density):
            densest[region] = row
    return densest


async def region_protection(session: AsyncSession, world_id: int) -> dict[int, ProtectedAreaRow]:
    query = (
        select(ProtectedAreaRow)
        .join(EntityRow, EntityRow.id == ProtectedAreaRow.region_entity_id)
        .where(EntityRow.world_id == world_id, ProtectedAreaRow.lifted_epoch.is_(None))
        .order_by(ProtectedAreaRow.id)
    )
    strongest: dict[int, ProtectedAreaRow] = {}
    for row in await session.scalars(query):
        if row.region_entity_id not in strongest or row.strength > strongest[row.region_entity_id].strength:
            strongest[row.region_entity_id] = row
    return strongest


async def region_waves(session: AsyncSession, world_id: int, since_epoch: int) -> dict[int, tuple[SeaWaveCoastRow, SeaWaveRow]]:
    query = (
        select(SeaWaveCoastRow, SeaWaveRow)
        .join(SeaWaveRow, SeaWaveRow.id == SeaWaveCoastRow.wave_id)
        .where(SeaWaveRow.world_id == world_id, SeaWaveRow.epoch >= since_epoch)
        .order_by(SeaWaveCoastRow.id)
    )
    highest: dict[int, tuple[SeaWaveCoastRow, SeaWaveRow]] = {}
    for coast, wave in (await session.execute(query)).all():
        if coast.region_entity_id not in highest or coast.height > highest[coast.region_entity_id][0].height:
            highest[coast.region_entity_id] = (coast, wave)
    return highest


async def region_groups(session: AsyncSession, world_id: int) -> dict[int, CreatureGroupRow]:
    query = (
        select(CreatureGroupRow)
        .join(EntityRow, EntityRow.id == CreatureGroupRow.region_entity_id)
        .where(EntityRow.world_id == world_id, CreatureGroupRow.size > 0)
        .order_by(CreatureGroupRow.id)
    )
    largest: dict[int, CreatureGroupRow] = {}
    for row in await session.scalars(query):
        if row.region_entity_id not in largest or row.size > largest[row.region_entity_id].size:
            largest[row.region_entity_id] = row
    return largest
