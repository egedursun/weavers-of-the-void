from aerona.engine.context import TickContext
from aerona.engine.disease.agents import AgentTally, keep_agents
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


PHASES = (Phase("disease_agents", disease_agents),)
