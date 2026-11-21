from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.interpretation.tend import tend_interpretations
from aerona.engine.phase import Phase


@reads("table.interpretations", "table.treaty_clauses")
@writes("table.interpretations", "table.treaty_clauses")
async def interpretation(ctx: TickContext) -> None:
    for key, value in asdict(await tend_interpretations(ctx)).items():
        ctx.count(f"interpretation_{key}", value)


PHASES = (Phase("interpretation", interpretation),)
