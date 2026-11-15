from aerona.engine.body.variants import BiologyTally, keep_biology
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads("table.biology_variants", "table.people_biology", "table.species_profiles")
@writes("table.biology_variants")
async def biology_variants(ctx: TickContext) -> None:
    tally = BiologyTally()
    await keep_biology(ctx, tally)
    count(ctx, "biology_variants", tally)


PHASES = (Phase("biology_variants", biology_variants),)
