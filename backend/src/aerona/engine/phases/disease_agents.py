from aerona.engine.context import TickContext
from aerona.engine.disease.agents import AgentTally, keep_agents
from aerona.engine.disease.paths import carry_by_paths
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "people.piety",
    "people.population",
    "settlement.piety",
    "settlement.population",
    "table.disease_agents",
    "table.disease_profiles",
    "table.endemic_diseases",
    "table.entities",
    "table.holder_levels",
    "table.node_births",
    "table.outbreaks",
    "table.species_ranges",
)
@writes(
    "people.piety",
    "settlement.piety",
    "table.chronicle",
    "table.chronicle_entities",
    "table.disease_agents",
    "table.disease_profiles",
    "table.endemic_diseases",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.outbreaks",
)
async def disease_agents(ctx: TickContext) -> None:
    tally = AgentTally()
    await keep_agents(ctx, tally)
    ctx.count("disease_agents_typed", tally.typed)
    ctx.count("disease_right_cures", tally.right)
    ctx.count("disease_wrong_cures", tally.wrong)
    ctx.count("disease_resistance_rose", tally.resistant)
    ctx.count("disease_agents_identified", tally.identified)
    ctx.count("disease_reservoirs", tally.reservoirs)


@reads(
    "settlement.population",
    "table.bonds",
    "table.community_cohorts",
    "table.disease_cures",
    "table.disease_profiles",
    "table.disease_routes",
    "table.divine_wounds",
    "table.drink_kinds",
    "table.endemic_diseases",
    "table.entities",
    "table.foreign_gods",
    "table.gathering_guests",
    "table.gatherings",
    "table.herds",
    "table.holder_techniques",
    "table.immunities",
    "table.impurity_sources",
    "table.kind_holdings",
    "table.ley_lines",
    "table.node_births",
    "table.nodes",
    "table.outbreaks",
    "table.plague_responses",
    "table.quarantines",
    "table.region_environment",
    "table.settlement_profiles",
    "table.sons",
    "table.species_hosts",
    "table.species_profiles",
    "table.species_ranges",
    "table.structure_profiles",
    "table.theory_adherents",
    "table.theory_profiles",
    "table.world_domain_hooks",
)
@writes("table.chronicle", "table.chronicle_entities", "table.incident_facts", "table.incident_participants", "table.incidents", "table.outbreaks")
async def disease_paths(ctx: TickContext) -> None:
    tally = await carry_by_paths(ctx)
    for path, count in sorted(tally.carried.items()):
        ctx.count(f"disease_carried.{path.value}", count)


PHASES = (Phase("disease_agents", disease_agents), Phase("disease_paths", disease_paths))
