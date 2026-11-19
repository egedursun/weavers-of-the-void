from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.discovery import ResearchIncident
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.models.entity_stats import SpeciesStats
from aerona.engine.ecology.control import commonest_species
from aerona.engine.lore.dangers import strike
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, entity, settlement


async def ranged_kind(session: AsyncSession, world: CoreWorld, name: str, region: EntityRow, abundance: int) -> EntityRow:
    species = await entity(session, name, EntityType.SPECIES, SpeciesStats(hp=40, intelligence=30), world_id=world.world.id, location_id=region.id)
    session.add(SpeciesRangeRow(species_entity_id=species.id, region_entity_id=region.id, abundance=abundance, fit=100, since_epoch=0, locked=[]))
    await session.flush()
    return species


async def test_a_released_beast_comes_from_a_kind_still_living_in_the_land(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0]
    gone = await ranged_kind(session, world, "Vanished Grazer", region, 90)
    living = await ranged_kind(session, world, "Lasting Grazer", region, 20)
    gone.status, gone.end_epoch = EntityStatus.DEAD, 1
    town = await settlement(session, "Workshop Town", world, region)
    await session.flush()
    ctx = await manual_context(session, "research_cycles")
    assert await commonest_species(ctx, region.id) == living.id
    await strike(ctx, town, ResearchIncident.RELEASED_BEAST)
    beasts = list(await session.scalars(select(EntityRow.name).where(EntityRow.entity_type == EntityType.BEAST)))
    assert f"The Great {living.name}" in beasts and f"The Great {gone.name}" not in beasts
    living.status, living.end_epoch = EntityStatus.DEAD, 1
    await session.flush()
    assert await commonest_species(ctx, region.id) is None
