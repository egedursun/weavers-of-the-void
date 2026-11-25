from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.foreign_gods import ForeignGodDraft, ForeignGodRepository
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import BeastStats, CosmicBeingStats
from aerona.domain.models.stats import StatBlock
from tests.engine.core.factories import CoreWorld, entity


async def foreign_god(session: AsyncSession, world: CoreWorld, name: str = "Ombrun") -> int:
    god = await ForeignGodRepository(session).create(ForeignGodDraft(name, world.world.id, Domain.STORM, 40, StatBlock.uniform(50), 1, title="the Old"))
    await session.flush()
    return god.id


async def beast(session: AsyncSession, world: CoreWorld, intelligence: int, name: str = "Grey Hunger") -> EntityRow:
    found = await entity(session, name, EntityType.BEAST, BeastStats(hp=60, danger=40), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(BeastProfileRow(beast_entity_id=found.id, intelligence=intelligence, hoard={}, locked=[]))
    await session.flush()
    return found


async def cosmic_being(session: AsyncSession, world: CoreWorld) -> EntityRow:
    return await entity(session, "Long Watcher", EntityType.COSMIC_BEING, CosmicBeingStats(size=50), world_id=world.world.id, location_id=world.regions[0].id)
