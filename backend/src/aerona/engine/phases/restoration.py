from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.restoration.rise import tend_restorations


@reads(
    "table.accounts",
    "table.claims",
    "table.de_jure_links",
    "table.entities",
    "table.nodes",
    "table.restorations",
    "table.settlement_profiles",
    "table.title_profiles",
    "table.titles",
)
@writes("table.applied_fixups", "table.bonds", "table.claims", "table.polity_profiles", "table.restorations", "table.titles")
async def restoration(ctx: TickContext) -> None:
    for key, value in asdict(await tend_restorations(ctx)).items():
        ctx.count(f"restoration_{key}", value)


PHASES = (Phase("restoration", restoration),)
