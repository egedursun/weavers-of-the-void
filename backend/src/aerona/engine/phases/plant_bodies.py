from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.plants.bodies import PlantTally, keep_plants


@reads(
    "table.creator",
    "table.dimensions",
    "table.entities",
    "table.forced_weather",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.node_births",
    "table.nodes",
    "table.plant_anatomy",
    "table.plant_parts",
    "table.plant_profiles",
    "table.region_crops",
    "table.region_environment",
    "table.sons",
    "table.species_products",
    "table.species_profiles",
    "table.species_ranges",
    "table.stars",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.plant_anatomy",
    "table.plant_parts",
    "table.region_crops",
    "table.species_products",
    "table.species_ranges",
)
async def plant_bodies(ctx: TickContext) -> None:
    tally = PlantTally()
    await keep_plants(ctx, tally)
    ctx.count("plants_grown", tally.grown)
    ctx.count("plant_goods", tally.goods)
    ctx.count("plant_crops_damaged", tally.damaged)
    ctx.count("plants_spread", tally.spread)
    ctx.count("plants_invaded", tally.invaded)
    ctx.count("plants_tamed", tally.tamed)


PHASES = (Phase("plant_bodies", plant_bodies),)
