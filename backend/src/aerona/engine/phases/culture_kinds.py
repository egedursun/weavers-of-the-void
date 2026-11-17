from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.kinds.culture_life import keep_culture_kinds
from aerona.engine.phase import Phase


@reads("table.aim_kinds", "table.culture_values", "table.fear_kinds", "table.kind_holdings", "table.reading_kinds", "table.tenet_kinds")
@writes("table.aim_kinds", "table.culture_values", "table.fear_kinds", "table.reading_kinds", "table.tenet_kinds")
async def culture_kinds(ctx: TickContext) -> None:
    tally = await keep_culture_kinds(ctx)
    ctx.count("culture_kinds_built_in", tally.built_in)
    ctx.count("tenets_held", tally.tenets)


PHASES = (Phase("culture_kinds", culture_kinds),)
