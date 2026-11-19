from aerona.engine.context import TickContext
from aerona.engine.forecasting.works import ForecastTally, keep_forecasting
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "people.piety",
    "settlement.prosperity",
    "table.celestial_readings",
    "table.community_relations",
    "table.creator",
    "table.dimensions",
    "table.entities",
    "table.folk_knowledge",
    "table.forced_weather",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.holder_levels",
    "table.memories",
    "table.monsoon_seasons",
    "table.node_births",
    "table.nodes",
    "table.observation_methods",
    "table.sons",
    "table.stars",
    "table.weather_works",
    "table.worlds",
)
@writes(
    "settlement.prosperity",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.entities",
    "table.forced_weather",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.observation_methods",
    "table.weather_works",
)
async def forecasting(ctx: TickContext) -> None:
    tally = ForecastTally()
    await keep_forecasting(ctx, tally)
    ctx.count("forecast_methods", tally.methods)
    ctx.count("forecasts_kept", tally.kept)
    ctx.count("forecasts_failed", tally.failed)
    ctx.count("forecasts_ignored", tally.ignored)
    ctx.count("weather_worked", tally.worked)
    ctx.count("weather_side_effects", tally.side_effects)
    ctx.count("weather_works_banned", tally.banned)


PHASES = (Phase("forecasting", forecasting),)
