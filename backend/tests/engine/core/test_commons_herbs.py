from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.needs import SHORTFALL_EFFECTS
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.society_depth import ShortfallEffect
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.household import gather_commons, harvest_goods
from aerona.engine.economy.stocks import holding
from aerona.engine.phases.environment import environment_survey
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, settlement, tuned_rules


async def test_every_green_land_gives_its_farmers_healing_herbs(session: AsyncSession, world: CoreWorld) -> None:
    await environment_survey(await manual_context(session, "survey", rules=tuned_rules()))
    town = await settlement(session, "Greenmere", world, world.regions[0], population=10000)
    ground = await session.get(RegionEnvironmentRow, world.regions[0].id)
    assert ground is not None
    ground.forest_cover, ground.wetland, ground.soil_fertility = 0, 0, 60
    await session.flush()
    ctx = await manual_context(session, "commons", rules=tuned_rules())
    gathered = await gather_commons(ctx, await EconomyBook.load(ctx), town, 50.0)
    expected = round(10000 * 0.5 * ctx.rules.economy.commons_herbs_per_1000_farmers / 1000 * 0.6)
    assert gathered[CommodityKind.HERBS] == expected > 0
    assert await holding(session, town.id, CommodityKind.HERBS) == expected


async def test_every_basic_need_is_met_from_a_community_s_own_land_in_any_age(session: AsyncSession, world: CoreWorld) -> None:
    await environment_survey(await manual_context(session, "survey", rules=tuned_rules()))
    town = await settlement(session, "Anyland", world, world.regions[0], population=10000)
    ground = await session.get(RegionEnvironmentRow, world.regions[0].id)
    assert ground is not None
    ground.forest_cover, ground.wetland, ground.soil_fertility, ground.roughness = 40, 40, 40, 40
    await session.flush()
    ctx = await manual_context(session, "commons", rules=tuned_rules())
    book = await EconomyBook.load(ctx)
    made = {kind for kind, amount in (await gather_commons(ctx, book, town, 50.0)).items() if amount > 0}
    made |= {kind for kind, amount in (await harvest_goods(ctx, book, town, 1.0, 50.0)).items() if amount > 0}
    met = {SHORTFALL_EFFECTS[kind] for kind in made if kind in SHORTFALL_EFFECTS}
    assert {ShortfallEffect.HUNGER, ShortfallEffect.COLD, ShortfallEffect.SICKNESS, ShortfallEffect.HERDS, ShortfallEffect.TOIL} <= met
