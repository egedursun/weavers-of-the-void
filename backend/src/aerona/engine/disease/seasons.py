from aerona.constants.units import PERCENT
from aerona.db.tables.environment import RegionEnvironmentRow, WorldSeasonRow
from aerona.domain.enums.environment import WeatherEffect
from aerona.engine.context import TickContext
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.environment.years import world_years


def sickly_season(book: EnvironmentBook, world_id: int) -> WorldSeasonRow | None:
    seasons = book.seasons_of(world_id)
    return max(seasons, key=lambda season: (season.rain_shift + season.temperature_shift, -season.position)) if seasons else None


def year_factor(ctx: TickContext, ground: RegionEnvironmentRow, season: WorldSeasonRow | None, wet: int, heat: int) -> float:
    table = ctx.rules.seasonal
    weather = 1 + wet / PERCENT * table.disease_wet_pct / PERCENT + heat / PERCENT * table.disease_heat_pct / PERCENT
    shift = season.rain_shift / PERCENT * ground.seasonality / PERCENT * table.disease_season_rain_pct / PERCENT if season is not None else 0.0
    return weather * (1 + shift)


def region_factor(ctx: TickContext, book: EnvironmentBook, ground: RegionEnvironmentRow) -> float:
    table = ctx.rules.seasonal
    season = sickly_season(book, ground.world_id)
    years = world_years(ctx.environment, ground.world_id, "disease")
    total = 0.0
    for year in years:
        weather = book.weather(ctx.environment.world_seed, ctx.epoch, ground, season, f"disease.{ground.entity_id}.{year.year}")
        total += year_factor(ctx, ground, season, weather.effect(WeatherEffect.WET), weather.effect(WeatherEffect.HEAT))
    mean = total / len(years) if years else 1.0
    mean *= 1 + book.spell_pull(ground).summer * ctx.rules.long_seasons.summer_sickness_pct / PERCENT / PERCENT
    return max(table.disease_season_floor_pct / PERCENT, min(table.disease_season_cap_pct / PERCENT, mean))


async def season_disease(ctx: TickContext, book: DiseaseBook) -> int:
    regions = {outbreak.region_entity_id for outbreak in book.outbreaks}
    if not regions:
        return 0
    ground = await EnvironmentBook.load(ctx.session, ctx.rules, ctx.epoch, book.atlas)
    for region_id in sorted(regions):
        env = ground.regions.get(region_id)
        if env is not None:
            book.seasonal[region_id] = region_factor(ctx, ground, env)
    for outbreak in book.outbreaks:
        outbreak.season_factor = round(book.seasonal.get(outbreak.region_entity_id, 1.0) * PERCENT)
    return len(book.seasonal)
