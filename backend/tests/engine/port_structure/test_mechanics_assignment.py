from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityOrigin, EntityType
from aerona.domain.enums.society import NaturalLaw, ResourceMechanic
from aerona.domain.models.entity_stats import NaturalLawStats, ResourceStats
from aerona.engine.gods.economy import mechanics_of
from aerona.engine.phases.mechanics_assignment import mechanics_assignment
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.mechanics import assign_mechanics, choose_law, resource_weighed
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld


async def record(session: AsyncSession, world: CoreWorld, name: str, entity_type: EntityType, description: str) -> EntityRow:
    stats: ResourceStats | NaturalLawStats = ResourceStats(abundance=50, value=40, might=20) if entity_type is EntityType.RESOURCE else NaturalLawStats()
    return await EntityRepository(session).create(
        EntityDraft(
            name=name,
            entity_type=entity_type,
            description=description,
            stats=stats,
            power_level=3,
            origin=EntityOrigin.ENGINE,
            birth_epoch=1,
            world_id=world.world.id,
            split_title=False,
        )
    )


async def test_resources_and_laws_take_chosen_mechanics_and_prose_never_decides(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    rotting = await record(session, world, "Moonfruit", EntityType.RESOURCE, "A soft fruit that rots within days of picking.")
    chosen = await record(session, world, "Glass Vein", EntityType.RESOURCE, "A plain vein of glass.")
    law = await record(session, world, "Law of Endless Harvest", EntityType.NATURAL_LAW, "Every season brings a rich harvest.")
    assert await assign_mechanics(session, rules, chosen, resource_choice=[ResourceMechanic.FIXED])
    assert await mechanics_of(session, chosen) == {ResourceMechanic.FIXED}
    before = choose_law(rules, law)
    law.description = "Nothing ever grows; every field is barren."
    law.name = "Law of the Barren Field"
    assert choose_law(rules, law) is before
    assert choose_law(rules, law, NaturalLaw.BOUNTY) is NaturalLaw.BOUNTY
    await mechanics_assignment(await manual_context(session, "test"))
    assert await resource_weighed(session, rotting)
    assert law.natural_law is before
    assert not await assign_mechanics(session, rules, rotting)
