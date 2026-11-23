from aerona.engine.body.variants import BiologyTally, keep_biology
from aerona.engine.body.w52_variants import keep_variant_ways
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads("table.biology_variants", "table.entities", "table.nodes", "table.people_biology", "table.species_profiles")
@writes("table.biology_variants")
async def biology_variants(ctx: TickContext) -> None:
    tally = BiologyTally()
    await keep_biology(ctx, tally)
    count(ctx, "biology_variants", tally)
    count(ctx, "biology_ways", await keep_variant_ways(ctx))


PHASES = (Phase("biology_variants", biology_variants),)
