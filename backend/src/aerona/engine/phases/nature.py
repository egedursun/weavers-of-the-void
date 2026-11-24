from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.nature.control import NatureRun, keep_nature
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads(
    "people.population",
    "settlement.population",
    "table.community_dishes",
    "table.community_stocks",
    "table.dishes",
    "table.entities",
    "table.entity_traits",
    "table.ferment_cultures",
    "table.nodes",
    "table.outbreaks",
    "table.people_biology",
    "table.plant_profiles",
    "table.region_environment",
    "table.region_pollution",
    "table.season_onsets",
    "table.sense_profiles",
    "table.soil_microbiota",
    "table.soil_nutrients",
    "table.species_profiles",
    "table.species_ranges",
    "table.species_relations",
    "table.trade_route_profiles",
    "table.world_seasons",
)
@writes("table.ferment_cultures", "table.sense_profiles", "table.soil_microbiota", "table.species_profiles", "table.species_ranges", "table.species_relations")
async def living_nature(ctx: TickContext) -> None:
    tally = NatureRun()
    await keep_nature(ctx, tally)
    for name in ("microbes", "symbiosis", "sleepers", "senses", "plants", "islands"):
        count(ctx, name, getattr(tally, name))


PHASES = (Phase("living_nature", living_nature),)
