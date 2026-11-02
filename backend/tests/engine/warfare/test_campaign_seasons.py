from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.weather import WEATHER
from aerona.db.tables.environment import PlaceEnvironmentRow, RegionEnvironmentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.warfare import BattleRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import PlaceCover, ScarKind, WaterSource, WeatherKind
from aerona.engine.environment.battleground import BattleGround, attack_factor, defend_factor, season_losses
from aerona.engine.environment.weather import Weather
from aerona.engine.phases.environment import environment_survey
from aerona.engine.phases.warfare import campaigns
from aerona.engine.services.war import declare_war
from aerona.rules.registry import Rules
from tests.engine.environment.factories import mapped_region
from tests.engine.society.factories import store_map
from tests.engine.warfare.factories import make, make_ctx, tune

RULES = Rules()
SEASONAL = {
    "battle_die": 1,
    "duel_chance": 0,
    "capture_chance": 0,
    "four_battle_exhaustion_chance": 0,
    "decisive_score": 50,
    "exhaustion_victory_margin": 50,
    "great_victory_diff": 1000,
    "battle_chance": 100,
    "season_engagement_pct": 100,
    "mobilization": 0,
}


def weather(kind: WeatherKind) -> Weather:
    spec = WEATHER[kind]
    return Weather(kind, spec.label, spec.effects(RULES))


def test_terrain_and_weather_shape_the_battle() -> None:
    clear = BattleGround(weather=weather(WeatherKind.CLEAR))
    storm = BattleGround(weather=weather(WeatherKind.BLIZZARD), night=True)
    assert attack_factor(RULES, storm) < attack_factor(RULES, clear)
    pass_ground = PlaceEnvironmentRow(
        entity_id=1, terrain=None, cover=PlaceCover.LIGHT, water_source=WaterSource.NONE, height_advantage=40, chokepoint=True, soil_fertility=50, locked=[]
    )
    assert defend_factor(RULES, BattleGround(place=pass_ground)) >= 1 + RULES.campaigns.chokepoint_defender_pct / 100
    assert season_losses(RULES, weather(WeatherKind.BLIZZARD), None, armour_pct=80, acclimatised=False) > season_losses(
        RULES, weather(WeatherKind.BLIZZARD), None, armour_pct=80, acclimatised=True
    )


async def test_wars_live_through_campaign_seasons(session: AsyncSession, world_id: int) -> None:
    region = await make(session, "Marches", EntityType.REGION, world_id, fertility=60)
    await store_map(session, world_id, [mapped_region(region.id, neighbours=[])])
    strong = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, location_id=region.id, population=9000, martiality=90)
    weak = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, location_id=region.id, population=9000, martiality=60)
    rules = tune(RULES, campaigns=SEASONAL)
    ctx = make_ctx(session, rules, epoch=10)
    await environment_survey(ctx)
    await declare_war(ctx, strong.id, weak.id, "old grudge")
    await campaigns(make_ctx(session, rules, epoch=10, phase="campaigns"))
    battles = list(await session.scalars(select(BattleRow)))
    assert len(battles) > 1
    assert all(battle.season_name is not None and battle.year is not None for battle in battles)
    ground = await session.get(RegionEnvironmentRow, region.id)
    assert ground is not None and ground.scars.get(ScarKind.BATTLEFIELD.value, 0) > 0
    texts = [row.text for row in await session.scalars(select(ChronicleRow))]
    assert any(" of " in text and "in the " in text for text in texts)
