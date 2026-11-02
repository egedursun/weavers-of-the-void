from sqlalchemy.ext.asyncio import AsyncSession

from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.war import WarEnding
from aerona.domain.models.entity_stats import ArtworkStats, CultStats, ItemStats, LawStats, PeopleStats, PlaceStats
from aerona.engine.phases.institutions import RecordEnd, cults, items, laws, order_end, peoples, swallowed_places, works
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, bond, entity, settlement
from tests.engine.cycles.factories import context, event, flags, tune, war

CERTAIN = {
    "repeal_conquest_chance": 100,
    "rigidity_resistance_pct": 0,
    "cult_merge_chance": 100,
    "cult_disband_chance": 100,
    "assimilation_chance": 100,
    "item_loss_chance": 100,
    "swallow_chance": 100,
}


def certain() -> Rules:
    return tune(Rules(), life_cycles=CERTAIN)


async def test_conquered_city_repeals_its_law_and_a_harsh_law_gnaws_prosperity(session: AsyncSession, world: CoreWorld) -> None:
    city = await settlement(session, "Grayport", world, world.regions[1], prosperity=50)
    law = await entity(session, "Iron Toll", EntityType.LAW, LawStats(rigidity=80, justice=10), world_id=world.world.id, location_id=city.id)
    row = await war(session, world, world.people, city, ended=10, victor=world.people)
    row.ending = WarEnding.CONQUEST
    await session.flush()
    assert await laws(context(session, world, certain(), 10)) == 1
    assert law.status is EntityStatus.DEAD and EntityFlag.REPEALED.value in await flags(session, law.id)
    assert stat(city, "prosperity") == 48


async def test_small_cult_joins_the_larger_cult_of_its_god_and_a_godless_one_disbands(session: AsyncSession, world: CoreWorld) -> None:
    large = await entity(session, "Great Choir", EntityType.CULT, CultStats(followers=1000, zeal=20, influence=60), world_id=world.world.id)
    small = await entity(session, "Small Choir", EntityType.CULT, CultStats(followers=50, zeal=20, influence=60), world_id=world.world.id)
    lonely = await entity(session, "Lonely Choir", EntityType.CULT, CultStats(followers=5, zeal=20, influence=5), world_id=world.world.id)
    for cult in (large, small):
        await bond(session, cult.id, world.son.id, BondKind.WORSHIPS)
    rules = tune(certain(), life_cycles={**CERTAIN, "cult_cap": 2})
    await cults(context(session, world, rules, 10))
    assert small.status is EntityStatus.DEAD and stat(large, "followers") == 1050
    assert lonely.status is EntityStatus.DEAD and EntityFlag.DISBANDED.value in await flags(session, lonely.id)


async def test_small_people_melts_into_its_large_neighbour(session: AsyncSession, world: CoreWorld) -> None:
    small = await entity(session, "Hill Folk", EntityType.PEOPLE, PeopleStats(population=500), world_id=world.world.id, location_id=world.regions[0].id)
    assert await peoples(context(session, world, certain(), 10)) == 1
    assert small.status is EntityStatus.DEAD and EntityFlag.ASSIMILATED.value in await flags(session, small.id)
    assert stat(world.people, "population") == 6400


async def test_uncarried_work_fades_and_is_forgotten(session: AsyncSession, world: CoreWorld) -> None:
    song = await entity(session, "Old Song", EntityType.ARTWORK, ArtworkStats(renown=3, influence=3), world_id=world.world.id, location_id=world.regions[2].id)
    assert await works(context(session, world, Rules(), 10)) == 1
    assert EntityFlag.FORGOTTEN.value in await flags(session, song.id)


async def test_unowned_item_in_the_wild_is_lost(session: AsyncSession, world: CoreWorld) -> None:
    blade = await entity(session, "Rusted Blade", EntityType.ITEM, ItemStats(might=0), world_id=world.world.id, location_id=world.regions[2].id)
    assert await items(context(session, world, certain(), 10)) == 1
    assert EntityFlag.LOST.value in await flags(session, blade.id)


async def test_severe_earthquake_swallows_a_place(session: AsyncSession, world: CoreWorld) -> None:
    grove = await entity(session, "Ash Grove", EntityType.PLACE, PlaceStats(danger=20), world_id=world.world.id, location_id=world.regions[2].id)
    await event(session, world, "Great Quake", EngineKind.EARTHQUAKE, severity=90, birth_epoch=10, location_id=world.regions[2].id)
    assert await swallowed_places(context(session, world, certain(), 10)) == 1
    assert grove.status is EntityStatus.DESTROYED and EntityFlag.SWALLOWED.value in await flags(session, grove.id)


async def test_the_god_orders_a_people_to_melt_into_its_neighbour(session: AsyncSession, world: CoreWorld) -> None:
    small = await entity(session, "Marsh Folk", EntityType.PEOPLE, PeopleStats(population=300), world_id=world.world.id, location_id=world.regions[0].id)
    await order_end(context(session, world, Rules(), 10), small.id, RecordEnd.ASSIMILATE, "the god willed it")
    assert small.status is EntityStatus.DEAD and stat(world.people, "population") == 6240
