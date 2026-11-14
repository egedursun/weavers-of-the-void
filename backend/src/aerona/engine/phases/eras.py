from aerona.engine.context import TickContext
from aerona.engine.eras.progress import EraTally, keep_eras
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads("table.cosmos", "table.holder_levels", "table.holder_techniques", "table.polity_profiles", "table.tech_programmes")
@writes("table.holder_levels")
async def tech_eras(ctx: TickContext) -> None:
    tally = EraTally()
    await keep_eras(ctx, tally)
    count(ctx, "tech_eras", tally)


PHASES = (Phase("tech_eras", tech_eras),)
