from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.standing.hypocrisy import HypocrisyTally, keep_hypocrisy


@reads("table.entities", "table.mortal_profiles", "table.professions_of_value")
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.mortal_profiles",
    "table.professions_of_value",
)
async def hypocrisy(ctx: TickContext) -> None:
    tally = HypocrisyTally()
    await keep_hypocrisy(ctx, tally)
    ctx.count("hypocrisy_faded", tally.faded)
    ctx.count("hypocrisy_exposed", tally.exposed)
    ctx.count("hypocrisy_forgiven", tally.forgiven)


PHASES = (Phase("hypocrisy", hypocrisy),)
