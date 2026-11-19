from aerona.engine.context import TickContext
from aerona.engine.eras.progress import EraTally, keep_eras
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count
from aerona.engine.technology.profiles import keep_technology


@reads(
    "knowledge.spread",
    "table.bonds",
    "table.cosmos",
    "table.custom_kinds",
    "table.entities",
    "table.holder_custom_techniques",
    "table.holder_levels",
    "table.holder_techniques",
    "table.nodes",
    "table.polity_profiles",
    "table.tech_programmes",
    "table.technology_profiles",
    "table.worlds",
)
@writes("table.entities", "table.holder_levels", "table.holder_techniques", "table.technology_profiles")
async def tech_eras(ctx: TickContext) -> None:
    tally = EraTally()
    await keep_eras(ctx, tally)
    count(ctx, "tech_eras", tally)
    await keep_technology(ctx)


PHASES = (Phase("tech_eras", tech_eras),)
