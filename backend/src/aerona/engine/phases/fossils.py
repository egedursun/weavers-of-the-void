from aerona.engine.context import TickContext
from aerona.engine.ecology.fossils import FossilTally, keep_fossils
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads(
    "table.constructs",
    "table.creator",
    "table.deep_passages",
    "table.dimensions",
    "table.entities",
    "table.entity_flags",
    "table.foreign_gods",
    "table.fossil_beds",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.goods_flows",
    "table.incident_participants",
    "table.incidents",
    "table.legend_profiles",
    "table.lifecycle_states",
    "table.node_births",
    "table.nodes",
    "table.notable_years",
    "table.outbreaks",
    "table.region_environment",
    "table.region_underground",
    "table.sons",
    "table.species_ranges",
    "table.stars",
    "table.structure_profiles",
    "table.theory_adherents",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_stocks",
    "table.entities",
    "table.fossil_beds",
    "table.goods_flows",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.legend_profiles",
    "table.notable_years",
    "table.outbreaks",
    "table.theory_adherents",
)
async def fossils(ctx: TickContext) -> None:
    tally = FossilTally()
    await keep_fossils(ctx, tally)
    count(ctx, "fossils", tally)


PHASES = (Phase("fossils", fossils),)
