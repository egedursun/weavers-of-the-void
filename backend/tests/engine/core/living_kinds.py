from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import SpeciesStats
from tests.engine.core.factories import CoreWorld, entity, surveyed


async def kind(session: AsyncSession, world: CoreWorld, name: str, region: EntityRow, abundance: int, **profile: object) -> EntityRow:
    species = await entity(session, name, EntityType.SPECIES, SpeciesStats(hp=30, intelligence=10), world_id=world.world.id, location_id=region.id)
    session.add(SpeciesProfileRow(species_entity_id=species.id, **profile))
    session.add(SpeciesRangeRow(species_entity_id=species.id, region_entity_id=region.id, abundance=abundance, fit=100, since_epoch=0, locked=[]))
    await session.flush()
    return species


async def range_of(session: AsyncSession, species: EntityRow, region: EntityRow) -> SpeciesRangeRow:
    row = await session.get(SpeciesRangeRow, (species.id, region.id))
    assert row is not None
    return row


async def land(session: AsyncSession, world: CoreWorld, region: EntityRow, **values: object) -> RegionEnvironmentRow:
    await surveyed(session, world)
    row = await session.get(RegionEnvironmentRow, region.id)
    assert row is not None
    for key, value in values.items():
        setattr(row, key, value)
    await session.flush()
    return row


async def told(session: AsyncSession, key: str) -> bool:
    return await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == key).limit(1)) is not None
