from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.water.ice import WaterTally, keep_water


@reads(
    "settlement.population",
    "settlement.prosperity",
    "table.coasts",
    "table.creator",
    "table.deep_passages",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.fossil_beds",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.local_climates",
    "table.node_births",
    "table.nodes",
    "table.outbreaks",
    "table.region_cryosphere",
    "table.region_environment",
    "table.river_shifts",
    "table.sediment_flows",
    "table.sons",
    "table.stars",
    "table.structure_profiles",
    "table.worlds",
)
@writes(
    "settlement.prosperity",
    "table.chronicle",
    "table.chronicle_entities",
    "table.coasts",
    "table.entities",
    "table.fossil_beds",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.local_climates",
    "table.outbreaks",
    "table.region_cryosphere",
    "table.region_environment",
    "table.sediment_flows",
)
async def water_and_ice(ctx: TickContext) -> None:
    tally = WaterTally()
    await keep_water(ctx, tally)
    ctx.count("water_ice_closed", tally.closed)
    ctx.count("water_ice_opened", tally.opened)
    ctx.count("water_thawed", tally.thawed)
    ctx.count("water_snow_droughts", tally.droughts)
    ctx.count("water_silted", tally.silted)
    ctx.count("water_coast_lost", tally.lost)
    ctx.count("water_delta_grew", tally.grew)
    ctx.count("water_glaciers", tally.glaciers)


PHASES = (Phase("water_and_ice", water_and_ice),)
