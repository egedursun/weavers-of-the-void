from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.world_views import WorldViewRow
from aerona.domain.enums.economy import CommodityKind, ExtractionKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.world import WorldType
from aerona.domain.enums.world_view import BindingNeed, SettleMode, WarTerrain, WorldLight
from aerona.engine.context import TickContext
from aerona.engine.cosmos.world_view_control import edit_view, restore_view
from aerona.engine.cosmos.world_views import ViewTally, default_view, keep_views, unfit_for_land_war, view_of
from aerona.engine.economy.extraction import world_share
from aerona.engine.economy.household import eat
from aerona.engine.environment.battleground import night_chance
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.settlement.book import town_of
from aerona.engine.settlement.life import fires
from tests.engine.core.factories import CoreWorld, settlement, tuned_rules


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "world_views", rules=tuned_rules(**rules))


async def test_every_world_takes_the_nature_of_its_kind_and_the_god_can_set_and_restore_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 2)
    iron = default_view(ctx.rules, WorldType.IRON)
    gas = default_view(ctx.rules, WorldType.GAS)
    assert iron.ore_yield_pct == ctx.rules.world_physics.iron_ore_yield and not gas.soil and gas.war is WarTerrain.SKY and unfit_for_land_war(gas)
    assert not default_view(ctx.rules, WorldType.HOLLOW).nights and default_view(ctx.rules, WorldType.HOLLOW).light is WorldLight.INNER_SUN
    tally = ViewTally()
    await keep_views(ctx, tally)
    row = await session.get(WorldViewRow, world.world.id)
    assert row is not None and tally.seeded >= 1 and row.ore_yield_pct == 100
    await edit_view(ctx, world.world.id, {"storm_pct": 250, "settle": "floating"}, [])
    view = await view_of(session, ctx.rules, world.world.id)
    assert view.storm_pct == 250 and view.settle is SettleMode.FLOATING and "storm_pct" in row.locked
    await restore_view(ctx, world.world.id)
    assert row.storm_pct == 100 and row.settle is SettleMode.GROUND and row.locked == []


async def test_a_town_bound_to_heat_burns_its_fuel_and_grows_restless_without_it(session: AsyncSession, world: CoreWorld) -> None:
    cold = await settlement(session, "Frostgate", world, world.regions[0], population=1000)
    warm = await settlement(session, "Emberhold", world, world.regions[1], population=1000)
    for town in (cold, warm):
        session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, unrest=0, locked=[]))
    session.add(CommunityStockRow(community_entity_id=warm.id, commodity=CommodityKind.FUEL, quantity=500, quality=50))
    await session.flush()
    ctx = await at(session, 2)
    await keep_views(ctx, ViewTally())
    await edit_view(ctx, world.world.id, {"need": BindingNeed.HEAT.value}, [])
    tally = ViewTally()
    await keep_views(await at(session, 3), tally)
    cold_profile = await session.get(SettlementProfileRow, cold.id)
    warm_profile = await session.get(SettlementProfileRow, warm.id)
    fuel = await session.scalar(select(CommunityStockRow.quantity).where(CommunityStockRow.community_entity_id == warm.id))
    assert cold_profile is not None and warm_profile is not None
    assert cold_profile.unrest == ctx.rules.world_views.shortfall_unrest and warm_profile.unrest == 0
    assert tally.short >= 1 and tally.met >= 1 and fuel is not None and fuel < 500


async def test_a_floating_town_pays_to_stay_aloft_and_suffers_when_it_cannot(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Cloudmere", world, world.regions[0], prosperity=50)
    await session.flush()
    ctx = await at(session, 2)
    await keep_views(ctx, ViewTally())
    await edit_view(ctx, world.world.id, {"settle": SettleMode.FLOATING.value}, [])
    tally = ViewTally()
    await keep_views(await at(session, 3), tally)
    assert tally.unpaid >= 1 and (stat(town, "prosperity") or 0) < 50


async def test_fire_does_not_burn_on_a_world_without_it(session: AsyncSession, world: CoreWorld) -> None:
    town_row = await settlement(session, "Stillair", world, world.regions[0], population=4000)
    session.add(SettlementProfileRow(settlement_entity_id=town_row.id, size_tier=SizeTier.TOWN, fire_risk=80, locked=[]))
    await session.flush()
    ctx = await at(session, 2)
    await keep_views(ctx, ViewTally())
    await edit_view(ctx, world.world.id, {"fire": False}, [])
    town = await town_of(ctx, town_row, await KnowledgeMap.load(session))
    assert await fires(ctx, town, None, await KnowledgeMap.load(session)) == 0 and town.profile.fire_risk == 0


async def test_ore_timber_harvests_food_and_nights_follow_the_nature_of_the_world(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 2)
    await keep_views(ctx, ViewTally())
    await edit_view(ctx, world.world.id, {"ore_yield_pct": 200, "timber_pct": 50, "soil": False, "light": "lava_glow", "food_need_pct": 0}, [])
    view = await view_of(session, ctx.rules, world.world.id)
    assert world_share(ctx.rules, view, ExtractionKind.MINING) == 2.0 and world_share(ctx.rules, view, ExtractionKind.LOGGING) == 0.5
    farming = ctx.rules.world_views.lava_light_pct / 100 * ctx.rules.world_views.soilless_harvest_pct / 100
    assert world_share(ctx.rules, view, ExtractionKind.FARMING) == farming and world_share(ctx.rules, view, ExtractionKind.FISHING) == 1.0
    assert night_chance(ctx.rules, False, 24) == 0.0 and night_chance(ctx.rules, True, 24) > 0
    town = await settlement(session, "Fastmoor", world, world.regions[0], population=900)
    await session.flush()
    meal = await eat(ctx, town)
    assert meal.fed_pct == 100


async def test_a_sealed_town_breathes_while_it_pays_its_upkeep(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Domehold", world, world.regions[0], population=1000)
    session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, unrest=0, locked=[]))
    await session.flush()
    ctx = await at(session, 2)
    await keep_views(ctx, ViewTally())
    await edit_view(ctx, world.world.id, {"need": BindingNeed.AIR.value, "settle": SettleMode.HABITAT.value}, [])
    set_stats(town, wealth=100)
    tally = ViewTally()
    await keep_views(await at(session, 3), tally)
    profile = await session.get(SettlementProfileRow, town.id)
    assert profile is not None and tally.upkept == 1 and tally.met == 1 and profile.unrest == 0
    set_stats(town, wealth=0)
    await keep_views(await at(session, 4), tally)
    assert tally.unpaid == 1 and tally.short == 1 and profile.unrest == ctx.rules.world_views.shortfall_unrest
