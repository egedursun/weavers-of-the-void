from sqlalchemy.ext.asyncio import AsyncSession

from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import PlaceStats, ProphecyStats
from aerona.engine.phases.living_stats import living_stats
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import add_flag, has_flag
from aerona.engine.primitives.stats import stat
from tests.engine.core.factories import CoreWorld, bond, entity, knowledge, settlement, tuned_rules


async def test_mysterious_places_yield_lost_knowledge_and_prophecies_wear(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(record_schema={"mystery_divisor": 1, "prophecy_grace": 0, "certainty_wear": 50})
    stones = PlaceStats(danger=10, fertility=20, mystery=90)
    place = await entity(session, "Weeping Stones", EntityType.PLACE, stones, world_id=world.world.id, location_id=world.regions[0].id)
    await settlement(session, "Stonewatch", world, world.regions[0])
    village = await settlement(session, "Underhill", world, world.regions[0])
    village.location_id = place.id
    lost = await knowledge(session, world, "Ash Script", KnowledgeBranch.WRITING)
    await add_flag(session, lost.id, EntityFlag.LOST, 1)
    prophecy = await entity(session, "The Red Dawn", EntityType.PROPHECY, ProphecyStats(certainty=60), world_id=world.world.id, creator_son_id=world.son.id)
    await bond(session, prophecy.id, village.id, BondKind.TELLS_OF)
    fame = world.son.fame
    await living_stats(await manual_context(session, "test", rules))
    assert not await has_flag(session, lost.id, EntityFlag.LOST)
    assert (stat(place, "mystery") or 0) < 90
    assert stat(prophecy, "certainty") == 10
    assert await has_flag(session, prophecy.id, EntityFlag.MOCKED)
    assert world.son.fame <= fame
