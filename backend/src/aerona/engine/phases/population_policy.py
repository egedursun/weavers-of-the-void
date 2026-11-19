from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.numbers.policies import keep_numbers
from aerona.engine.phase import Phase


@reads(
    "settlement.population",
    "table.entities",
    "table.mind_profiles",
    "table.mortal_profiles",
    "table.nodes",
    "table.polity_members",
    "table.polity_profiles",
    "table.population_instruments",
    "table.population_policies",
    "table.pressures",
    "table.settlement_profiles",
)
@writes(
    "settlement.population",
    "table.chronicle",
    "table.chronicle_entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.mortal_profiles",
    "table.polity_profiles",
    "table.population_instruments",
    "table.population_policies",
    "table.settlement_profiles",
)
async def population_policy(ctx: TickContext) -> None:
    tally = await keep_numbers(ctx)
    ctx.count("population_enforced", tally.enforced)
    ctx.count("population_resisted", tally.resisted)
    ctx.count("population_expelled", tally.expelled)
    ctx.count("population_resettled", tally.resettled)
    ctx.count("population_targets_met", tally.met)
    ctx.count("population_adopted", tally.adopted)
    ctx.count("population_repealed", tally.repealed)


PHASES = (Phase("population_policy", population_policy),)
