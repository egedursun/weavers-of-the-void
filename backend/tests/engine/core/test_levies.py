from sqlalchemy.ext.asyncio import AsyncSession

from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import ArmyStats, PeopleStats
from aerona.engine.primitives.levies import demobilise, stand_down
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, entity


async def test_soldiers_sent_home_to_a_people_below_its_floor_never_count_for_more_than_were_sent(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    folk = await entity(session, "The Thinned Folk", EntityType.PEOPLE, PeopleStats(population=0), world_id=world.world.id, location_id=world.regions[0].id)
    assert demobilise(rules, folk, 4) <= 4
    host = await entity(session, "The Last Host", EntityType.ARMY, ArmyStats(size=38), world_id=world.world.id, location_id=world.regions[0].id)
    returned = stand_down(rules, host, folk)
    assert 0 <= returned <= 38 and (stat(host, "size") or 0) == 0
