from sqlalchemy.ext.asyncio import AsyncSession

from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import MortalStats
from aerona.rules.registry import Rules
from aerona.services.books.model import LIFESPAN_WITH_CARE, BookBuilder
from tests.services.app.factories import Cosmos, make_entity


def stats_for(age: int) -> MortalStats:
    return MortalStats(hp=60, strength=40, agility=40, intellect=40, charisma=95, age=age, lifespan=70)


async def test_a_mortal_past_its_lifespan_shows_the_span_it_was_given(session: AsyncSession, world: Cosmos) -> None:
    elder = await make_entity(session, "Old Seer", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id, stats=stats_for(80))
    youth = await make_entity(session, "Young Seer", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id, stats=stats_for(30))
    builder = BookBuilder(session, Rules())
    await builder.load_common()
    told = {item.label: item.value for item in (await builder.entity_article(elder)).stats}
    assert int(told[LIFESPAN_WITH_CARE]) > int(told["Lifespan"])
    assert LIFESPAN_WITH_CARE not in {item.label for item in (await builder.entity_article(youth)).stats}
