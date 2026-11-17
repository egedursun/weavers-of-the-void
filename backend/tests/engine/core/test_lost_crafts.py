from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.culture import HolderLevelRow
from aerona.db.tables.ecology import SpeciesProductRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import SpeciesStats
from aerona.engine.ecology.extinction import lost_crafts
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, entity


async def test_the_last_kind_that_yields_a_craft_takes_the_craft_with_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "extinction")
    serpent = await entity(session, "Ash Serpent", EntityType.SPECIES, SpeciesStats(), world_id=world.world.id)
    session.add(SpeciesProductRow(species_entity_id=serpent.id, product="venom"))
    craft = HolderLevelRow(holder_entity_id=world.people.id, branch=KnowledgeBranch.MEDICINE, level=3)
    kept = HolderLevelRow(holder_entity_id=world.people.id, branch=KnowledgeBranch.MAGIC, level=3, locked=["level"])
    session.add_all([craft, kept])
    await session.flush()
    assert await lost_crafts(ctx, serpent) == 1
    assert craft.level == 3 - ctx.rules.extinction.craft_loss and kept.level == 3


async def test_a_craft_another_kind_still_feeds_is_kept(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "extinction")
    serpent = await entity(session, "Ash Serpent", EntityType.SPECIES, SpeciesStats(), world_id=world.world.id)
    cousin = await entity(session, "Reed Serpent", EntityType.SPECIES, SpeciesStats(), world_id=world.world.id)
    session.add_all([SpeciesProductRow(species_entity_id=serpent.id, product="venom"), SpeciesProductRow(species_entity_id=cousin.id, product="venom")])
    craft = HolderLevelRow(holder_entity_id=world.people.id, branch=KnowledgeBranch.MEDICINE, level=3)
    session.add(craft)
    await session.flush()
    assert await lost_crafts(ctx, serpent) == 0 and craft.level == 3
