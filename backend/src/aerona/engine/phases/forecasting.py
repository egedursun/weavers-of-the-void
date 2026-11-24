from aerona.engine.context import TickContext
from aerona.engine.forecasting.works import ForecastTally, keep_forecasting
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "people.piety",
    "settlement.prosperity",
    "settlement.wealth",
    "table.bonds",
    "table.celestial_readings",
    "table.community_relations",
    "table.creator",
    "table.culture_ethics",
    "table.culture_values",
    "table.deed_claims",
    "table.deeds",
    "table.deep_passages",
    "table.dimensions",
    "table.entities",
    "table.folk_knowledge",
    "table.forced_weather",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.geasa",
    "table.genius_loci",
    "table.held_identities",
    "table.holder_levels",
    "table.incident_participants",
    "table.memories",
    "table.mind_profiles",
    "table.monsoon_seasons",
    "table.node_births",
    "table.nodes",
    "table.observation_methods",
    "table.offices",
    "table.personality_values",
    "table.polity_members",
    "table.professions_of_value",
    "table.region_cryosphere",
    "table.region_environment",
    "table.relationships",
    "table.reputations",
    "table.settlement_profiles",
    "table.sons",
    "table.stars",
    "table.tradition_profiles",
    "table.traits",
    "table.war_sides",
    "table.wars",
    "table.weather_works",
    "table.world_maps",
    "table.worlds",
)
@writes(
    "settlement.prosperity",
    "settlement.wealth",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.deed_claims",
    "table.deeds",
    "table.entities",
    "table.forced_weather",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.memories",
    "table.observation_methods",
    "table.polity_profiles",
    "table.professions_of_value",
    "table.reputations",
    "table.settlement_profiles",
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
    ctx.count("weather_works_raised", tally.raised)


PHASES = (Phase("forecasting", forecasting),)
