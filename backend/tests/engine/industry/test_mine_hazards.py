from sqlalchemy import select

from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.economy import CommodityKind, HazardKind
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.models.entity_stats import ResourceStats
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.extraction import region_key, strike_hazard
from aerona.engine.primitives.stats import stat
from tests.engine.industry.test_industry import ground
from tests.engine.society.factories import Realm, context, make, mortal, settlement, tuned


async def test_a_cave_in_kills_and_maims_miners_seals_the_mine_and_may_wake_a_deep_thing(realm: Realm) -> None:
    ctx = context(realm.session, tuned(mining_hazards={"cavern_chance": 100}))
    town = await settlement(realm, "Hexley", population=2000)
    lode = await make(realm.session, "Iron Hill", EntityType.RESOURCE, ResourceStats(abundance=50), world_id=realm.world.id, location_id=realm.region.id)
    profile = ResourceProfileRow(
        resource_entity_id=lode.id, commodity=CommodityKind.ORE, reserve=100, initial_reserve=100, richness=50, extraction_difficulty=50, quality=50
    )
    realm.session.add(profile)
    miner = await mortal(realm, "Ulf", location_id=town.id, role=MortalRole.ARTISAN)
    miner.affiliated_entity_id = town.id
    await realm.session.flush()
    book = await EconomyBook.load(ctx)
    book.ground.regions[realm.region.id] = ground(realm)
    assert region_key(book, lode.id) == realm.region.id
    hp = stat(miner, "hp") or 0
    await strike_hazard(ctx, book, lode, profile, town, workers=500, hazard=HazardKind.CAVE_IN)
    assert (stat(town, "population") or 0) < 2000
    assert profile.sealed_until_epoch == ctx.epoch + ctx.rules.mining_hazards.seal_epochs
    assert (stat(miner, "hp") or 0) < hp
    beast = await realm.session.scalar(select(EntityRow).where(EntityRow.subtype == "cavern beast"))
    assert beast is not None and beast.location_id == realm.region.id
