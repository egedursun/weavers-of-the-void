from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.weather import WEATHER
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.water import RegionCryosphereRow
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import SeasonWarmth, TerrainKind, WeatherKind, WeatherTrait
from aerona.domain.enums.forecasting import WeatherAim
from aerona.domain.enums.structure import StructureKind
from aerona.domain.models.entity_stats import StructureStats
from aerona.engine.economy.stocks import goods_of, lots_of
from aerona.engine.environment.glaze import ColdHarm, late_frost_loss, suffer_cold
from aerona.engine.environment.weather import WeatherInputs, weather_weights
from aerona.engine.forecasting.works import aimed_weather
from aerona.engine.military.vessels import icing
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import entity, seed_core_world, settlement, surveyed

RULES = Rules()
COLD = RULES.weather.cold_threshold


def weights(temperature: int, rainfall: int, warmth: SeasonWarmth = SeasonWarmth.EVEN) -> dict[WeatherKind, float]:
    return weather_weights(RULES, WeatherInputs(1, temperature, rainfall, 50, 0, TerrainKind.PLAIN, season_warmth=warmth))


def test_frost_and_ice_storm_carry_their_traits() -> None:
    assert {WeatherTrait.COLD, WeatherTrait.ICY} <= WEATHER[WeatherKind.FROST].traits
    assert {WeatherTrait.ICY, WeatherTrait.STORM, WeatherTrait.WET} <= WEATHER[WeatherKind.ICE_STORM].traits


def test_frost_falls_on_dry_air_near_freezing_and_more_as_seasons_turn() -> None:
    near = weights(COLD + 5, 10)
    assert near[WeatherKind.FROST] > 0 and weights(COLD + 40, 10)[WeatherKind.FROST] == 0
    assert weights(COLD + 5, 10, SeasonWarmth.WARMING)[WeatherKind.FROST] > near[WeatherKind.FROST]
    assert weights(COLD + 5, 100)[WeatherKind.FROST] == 0


def test_ice_storm_falls_on_wet_air_at_the_freezing_line() -> None:
    assert weights(COLD, 80)[WeatherKind.ICE_STORM] > 0
    assert weights(COLD + RULES.weather.glaze_band + 5, 80)[WeatherKind.ICE_STORM] == 0
    assert weights(COLD, 0)[WeatherKind.ICE_STORM] == 0


def test_cold_works_raise_frost_on_dry_land_and_ice_storm_on_wet_and_hulls_ice() -> None:
    wet = RegionEnvironmentRow(temperature=COLD, rainfall=80)
    dry = RegionEnvironmentRow(temperature=COLD + 5, rainfall=10)
    assert aimed_weather(RULES, WeatherAim.COLD, wet) is WeatherKind.ICE_STORM
    assert aimed_weather(RULES, WeatherAim.COLD, dry) is WeatherKind.FROST
    assert icing(RULES, 100, stormy=False, icy=False) == 100
    assert icing(RULES, 100, stormy=True, icy=True) == 100 + RULES.weather.icing_hull_pct
    assert icing(RULES, 100, stormy=False, icy=True) == RULES.weather.icing_hull_pct


async def test_frost_freezes_the_ground_and_an_ice_storm_breaks_works_timber_and_herds(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    ctx = await manual_context(session, "test", RULES)
    region = world.regions[0].id
    land = await session.get(RegionEnvironmentRow, region)
    assert land is not None
    land.forest_cover, land.locked = 60, []
    town = await settlement(session, "Rimehold", world, world.regions[0])
    barn = await entity(session, "Long Barn", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=region)
    session.add(StructureProfileRow(structure_entity_id=barn.id, kind=StructureKind.TEMPLE, condition=100))
    await goods_of(session, 0).add(town.id, CommodityKind.LIVESTOCK, 100, GoodsFlow.PRODUCTION)
    await session.flush()
    harm = ColdHarm(frosts={region: 2}, late_frosts={region: late_frost_loss(ctx, 80)}, ice_storms={region})
    assert harm.late_frosts[region] == 80 * RULES.weather.late_frost_growth_pct // 100
    await suffer_cold(ctx, harm, {region: land})
    frozen = await session.get(RegionCryosphereRow, region)
    barn_profile = await session.get(StructureProfileRow, barn.id)
    assert frozen is not None and frozen.frozen_depth >= 2 * RULES.weather.frost_ground_depth
    assert barn_profile is not None and barn_profile.condition == 100 - RULES.weather.ice_storm_structure_harm
    assert land.forest_cover == 60 - 60 * RULES.weather.ice_storm_timber_loss_pct // 100
    herd = sum(row.quantity for row in await lots_of(session, town.id, CommodityKind.LIVESTOCK))
    assert herd == 100 - RULES.weather.ice_storm_herd_loss_pct
    assert {"weather.ice_storm_harm", "weather.late_frost"} <= set(await session.scalars(select(IncidentRow.kind)))
