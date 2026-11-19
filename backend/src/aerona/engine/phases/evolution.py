from aerona.engine.context import TickContext
from aerona.engine.cosmos.cycles import CycleTally, turn_cycles
from aerona.engine.disease.carriers import CarrierTally, keep_carriers
from aerona.engine.disease.evolution import PathogenTally, evolve_pathogens
from aerona.engine.disease.research import ResearchTally, research_cures
from aerona.engine.disease.responses import ResponseTally, respond
from aerona.engine.disease.spillover import SpilloverTally, spill
from aerona.engine.disease.vaccination import VaccinationTally, vaccinate
from aerona.engine.ecology.evolution import EvolutionTally, evolve_traits
from aerona.engine.ecology.feral import FeralTally, run_wild
from aerona.engine.ecology.keystones import KeystoneTally, keep_services
from aerona.engine.ecology.lineages import LineageTally, mark_lineages
from aerona.engine.ecology.niches import NicheTally, keep_niches
from aerona.engine.ecology.trophic import TrophicTally, balance_food_chain
from aerona.engine.environment.succession import SuccessionTally, grow_lands
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads(
    "species.intelligence",
    "table.bonds",
    "table.entity_traits",
    "table.region_environment",
    "table.species_profiles",
    "table.species_ranges",
    "table.species_traits",
    "table.trait_history",
)
@writes("table.species_traits", "table.trait_history")
async def trait_evolution(ctx: TickContext) -> None:
    tally = EvolutionTally()
    await evolve_traits(ctx, tally)
    count(ctx, "trait", tally)


@reads(
    "table.creator",
    "table.dimensions",
    "table.entities",
    "table.entity_flags",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.incident_participants",
    "table.incidents",
    "table.node_births",
    "table.nodes",
    "table.sons",
    "table.species_profiles",
    "table.species_ranges",
    "table.species_traits",
    "table.stars",
    "table.worlds",
)
@writes("table.chronicle", "table.chronicle_entities", "table.incident_facts", "table.incident_participants", "table.incidents", "table.species_ranges")
async def niches(ctx: TickContext) -> None:
    tally = NicheTally()
    await keep_niches(ctx, tally)
    count(ctx, "niche", tally)


@reads("table.region_environment", "table.species_profiles", "table.species_ranges", "table.trophic_levels")
@writes("table.species_ranges", "table.trophic_levels")
async def trophic_flow(ctx: TickContext) -> None:
    tally = TrophicTally()
    await balance_food_chain(ctx, tally)
    count(ctx, "trophic", tally)


@reads("table.ecosystem_services", "table.entity_traits", "table.species_profiles", "table.species_ranges")
async def keystones(ctx: TickContext) -> None:
    tally = KeystoneTally()
    await keep_services(ctx, tally)
    count(ctx, "keystone", tally)


@reads("table.entities", "table.herds", "table.nodes", "table.species_profiles")
async def feral_reversion(ctx: TickContext) -> None:
    tally = FeralTally()
    await run_wild(ctx, tally)
    count(ctx, "feral", tally)


@reads("table.region_environment", "table.species_profiles", "table.species_ranges")
async def lineages(ctx: TickContext) -> None:
    tally = LineageTally()
    await mark_lineages(ctx, tally)
    count(ctx, "lineage", tally)


@reads(
    "settlement.population",
    "table.community_cohorts",
    "table.disease_cures",
    "table.disease_profiles",
    "table.drink_kinds",
    "table.endemic_diseases",
    "table.entities",
    "table.herds",
    "table.holder_techniques",
    "table.immunities",
    "table.impurity_sources",
    "table.kind_holdings",
    "table.ley_lines",
    "table.nodes",
    "table.outbreaks",
    "table.plague_responses",
    "table.quarantines",
    "table.settlement_profiles",
    "table.sons",
    "table.species_hosts",
    "table.species_profiles",
    "table.species_ranges",
    "table.structure_profiles",
    "table.theory_adherents",
    "table.theory_profiles",
)
async def pathogen_evolution(ctx: TickContext) -> None:
    tally = PathogenTally()
    await evolve_pathogens(ctx, tally)
    count(ctx, "pathogen", tally)


@reads(
    "settlement.population",
    "table.community_cohorts",
    "table.disease_carriers",
    "table.disease_cures",
    "table.disease_profiles",
    "table.drink_kinds",
    "table.endemic_diseases",
    "table.entities",
    "table.herds",
    "table.holder_techniques",
    "table.immunities",
    "table.impurity_sources",
    "table.kind_holdings",
    "table.ley_lines",
    "table.nodes",
    "table.outbreaks",
    "table.plague_responses",
    "table.quarantines",
    "table.settlement_profiles",
    "table.sons",
    "table.species_hosts",
    "table.species_profiles",
    "table.species_ranges",
    "table.structure_profiles",
    "table.theory_adherents",
    "table.theory_profiles",
)
async def carriers(ctx: TickContext) -> None:
    tally = CarrierTally()
    await keep_carriers(ctx, tally)
    count(ctx, "carrier", tally)


@reads(
    "settlement.population",
    "table.community_cohorts",
    "table.disease_cures",
    "table.disease_profiles",
    "table.drink_kinds",
    "table.endemic_diseases",
    "table.entities",
    "table.herds",
    "table.holder_techniques",
    "table.immunities",
    "table.impurity_sources",
    "table.kind_holdings",
    "table.ley_lines",
    "table.nodes",
    "table.outbreaks",
    "table.plague_responses",
    "table.quarantines",
    "table.settlement_profiles",
    "table.sons",
    "table.species_hosts",
    "table.species_profiles",
    "table.species_ranges",
    "table.structure_profiles",
    "table.theory_adherents",
    "table.theory_profiles",
)
async def spillover(ctx: TickContext) -> None:
    tally = SpilloverTally()
    await spill(ctx, tally)
    count(ctx, "spillover", tally)


@reads("table.outbreaks", "table.plague_responses")
async def plague_responses(ctx: TickContext) -> None:
    tally = ResponseTally()
    await respond(ctx, tally)
    count(ctx, "plague_response", tally)


@reads(
    "settlement.population",
    "table.community_cohorts",
    "table.disease_cures",
    "table.disease_profiles",
    "table.drink_kinds",
    "table.endemic_diseases",
    "table.entities",
    "table.herds",
    "table.holder_techniques",
    "table.immunities",
    "table.impurity_sources",
    "table.kind_holdings",
    "table.ley_lines",
    "table.nodes",
    "table.outbreaks",
    "table.plague_responses",
    "table.quarantines",
    "table.settlement_profiles",
    "table.sons",
    "table.species_hosts",
    "table.species_profiles",
    "table.species_ranges",
    "table.structure_profiles",
    "table.theory_adherents",
    "table.theory_profiles",
)
async def vaccination(ctx: TickContext) -> None:
    tally = VaccinationTally()
    await vaccinate(ctx, tally)
    count(ctx, "vaccination", tally)


@reads("table.disease_cures", "table.entities", "table.nodes", "table.outbreaks", "table.structure_profiles", "table.theory_adherents", "table.theory_profiles")
async def cure_research(ctx: TickContext) -> None:
    tally = ResearchTally()
    await research_cures(ctx, tally)
    count(ctx, "cure", tally)


@reads("table.region_environment")
@writes("table.region_environment")
async def biome_succession(ctx: TickContext) -> None:
    tally = SuccessionTally()
    await grow_lands(ctx, tally)
    count(ctx, "succession", tally)


@reads("table.region_environment", "table.trophic_levels", "table.world_cycles", "table.world_physics")
@writes("table.world_cycles", "table.world_physics")
async def world_cycles(ctx: TickContext) -> None:
    tally = CycleTally()
    await turn_cycles(ctx, tally)
    count(ctx, "cycle", tally)


PHASES = (
    Phase("trait_evolution", trait_evolution),
    Phase("niches", niches),
    Phase("trophic_flow", trophic_flow),
    Phase("keystones", keystones),
    Phase("feral_reversion", feral_reversion),
    Phase("lineages", lineages),
    Phase("pathogen_evolution", pathogen_evolution),
    Phase("carriers", carriers),
    Phase("spillover", spillover),
    Phase("plague_responses", plague_responses),
    Phase("vaccination", vaccination),
    Phase("cure_research", cure_research),
    Phase("biome_succession", biome_succession),
    Phase("world_cycles", world_cycles),
)
