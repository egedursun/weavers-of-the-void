from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.engine.primitives.manual import manual_context
from aerona.engine.services.war import open_war
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, settlement


async def test_a_war_is_named_after_the_two_sides_that_fight_it(session: AsyncSession, world: CoreWorld) -> None:
    attacker = await settlement(session, "Keelmouth", world, world.regions[0])
    defender = await settlement(session, "Reedholm", world, world.regions[0])
    war = await open_war(await manual_context(session, "war_names", Rules()), attacker, defender)
    event = await session.get(EntityRow, war.event_entity_id)
    assert event is not None and event.name == "War of Keelmouth and Reedholm"
