from sqlalchemy import select

from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.environment import RegionEnvironmentRow, WorldSeasonRow
from aerona.engine.context import TickContext
from aerona.engine.environment.book import active_sky, forced_weather
from aerona.engine.environment.season_shape import season_of_index
from aerona.engine.environment.weather import Weather, WeatherInputs, weather_at, weather_of
from aerona.engine.primitives.distance import RegionAtlas

PERCENT_SCALE = 100


async def weather_here(ctx: TickContext, entity_id: int, slot: str, atlas: RegionAtlas | None = None) -> Weather | None:
    atlas = atlas or await RegionAtlas.load(ctx.session)
    region_id = atlas.top_region(entity_id)
    ground = await ctx.session.get(RegionEnvironmentRow, region_id) if region_id is not None else None
    if ground is None:
        return None
    seasons = list(await ctx.session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id == ground.world_id).order_by(WorldSeasonRow.position)))
    season = season_of_index(seasons, ctx.epoch)
    for row in (await forced_weather(ctx.session, ctx.epoch)).get(ground.entity_id, []):
        if row.season_position is None or (season is not None and season.position == row.season_position):
            return weather_of(ctx.rules, row.kind)
    world = await ctx.session.get(WorldRow, ground.world_id)
    sky = await active_sky(ctx.session, ctx.epoch)
    scale = ground.seasonality / PERCENT_SCALE
    inputs = WeatherInputs(
        region_id=ground.entity_id,
        temperature=ground.temperature,
        rainfall=ground.rainfall,
        latitude=ground.latitude,
        magic_density=ground.magic_density,
        terrain=ground.dominant_terrain,
        leakage=world.leakage if world is not None else 0,
        season_temperature=round(season.temperature_shift * scale) if season is not None else 0,
        season_rain=round(season.rain_shift * scale) if season is not None else 0,
        sky=sky.get(ground.world_id, frozenset()) | sky.get(None, frozenset()),
    )
    return weather_at(ctx.rules, ctx.environment.world_seed, ctx.epoch, slot, inputs)
