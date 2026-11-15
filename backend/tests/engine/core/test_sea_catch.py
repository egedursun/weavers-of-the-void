from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.environment import CoastKind
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.household import harvest_goods
from aerona.engine.phases.environment import environment_survey
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, settlement, tuned_rules


async def test_a_town_s_fishers_catch_the_same_whatever_the_soil_of_its_land(session: AsyncSession, world: CoreWorld) -> None:
    await environment_survey(await manual_context(session, "survey", rules=tuned_rules()))
    town = await settlement(session, "Netwater", world, world.regions[0], population=2000)
    ground = await session.get(RegionEnvironmentRow, world.regions[0].id)
    assert ground is not None
    ground.coast_kind = CoastKind.BEACH
    session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.TOOLS, quantity=1000, quality=50))
    await session.flush()
    ctx = await manual_context(session, "catch", rules=tuned_rules())
    book = await EconomyBook.load(ctx)
    poor = await harvest_goods(ctx, book, town, 0.2, 50.0)
    rich = await harvest_goods(ctx, book, town, 2.0, 50.0)
    assert poor[CommodityKind.FISH] > 0 and abs(poor[CommodityKind.FISH] - rich[CommodityKind.FISH]) <= 1
    assert rich[CommodityKind.LIVESTOCK] > poor[CommodityKind.LIVESTOCK]
