from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.grave_goods.robbery import tend_graves
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads("table.bonds", "table.entities", "table.grave_goods", "table.nodes", "table.structure_profiles")
@writes("table.applied_fixups", "table.bonds", "table.crime_cases", "table.grave_goods", "table.memories")
async def grave_goods(ctx: TickContext) -> None:
    for key, value in asdict(await tend_graves(ctx)).items():
        ctx.count(f"graves_{key}", value)


PHASES = (Phase("grave_goods", grave_goods),)
