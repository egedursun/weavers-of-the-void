from aerona.engine.climes.crossings import CrossingTally, keep_cultures, keep_windows
from aerona.engine.climes.seasons import SeasonTally, keep_seasons
from aerona.engine.climes.winds import WindTally, keep_winds
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads(
    "settlement.prosperity",
    "table.climate_oscillations",
    "table.creator",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.incident_participants",
    "table.incidents",
    "table.monsoon_seasons",
    "table.node_births",
    "table.nodes",
    "table.region_environment",
    "table.region_pollution",
    "table.region_winds",
    "table.sons",
    "table.species_ranges",
    "table.stars",
    "table.world_maps",
    "table.world_physics",
    "table.worlds",
)
@writes(
    "settlement.prosperity",
    "table.chronicle",
    "table.chronicle_entities",
    "table.climate_oscillations",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.monsoon_seasons",
    "table.notable_years",
    "table.region_environment",
    "table.region_pollution",
    "table.region_winds",
    "table.species_ranges",
)
async def climes(ctx: TickContext) -> None:
    winds, seasons = WindTally(), SeasonTally()
    await keep_winds(ctx, winds)
    await keep_seasons(ctx, seasons)
    count(ctx, "winds", winds)
    count(ctx, "seasons", seasons)


@reads("table.cosmopolitan_cultures", "table.journeys", "table.nodes", "table.routes", "table.worlds")
async def crossings(ctx: TickContext) -> None:
    tally = CrossingTally()
    await keep_windows(ctx, tally)
    await keep_cultures(ctx, tally)
    count(ctx, "crossings", tally)


PHASES = (
    Phase("climes", climes),
    Phase("crossings", crossings),
)
