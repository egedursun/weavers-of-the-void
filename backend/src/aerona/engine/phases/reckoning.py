from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.reckoning.tend import tend_reckonings


@reads("table.incident_collections", "table.incidents", "table.offices", "table.reckoning_cases", "table.reckoning_measures", "table.reckonings")
@writes(
    "table.accounts", "table.applied_fixups", "table.offices", "table.polity_profiles", "table.reckoning_cases", "table.reckoning_measures", "table.reckonings"
)
async def reckoning(ctx: TickContext) -> None:
    for key, value in asdict(await tend_reckonings(ctx)).items():
        ctx.count(f"reckoning_{key}", value)


PHASES = (Phase("reckoning", reckoning),)
