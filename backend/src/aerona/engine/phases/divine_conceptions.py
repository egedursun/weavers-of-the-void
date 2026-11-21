from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.divine_conceptions.tend import tend_conceptions
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "table.bonds",
    "table.creator",
    "table.cult_doctrines",
    "table.cult_tenets",
    "table.dimensions",
    "table.divine_conceptions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.god_readings",
    "table.incident_participants",
    "table.incidents",
    "table.nodes",
    "table.reverences",
    "table.skills",
    "table.sons",
    "table.stars",
    "table.worlds",
)
@writes("table.applied_fixups", "table.bonds", "table.divine_conceptions", "table.entities", "table.god_readings")
async def divine_conceptions(ctx: TickContext) -> None:
    for key, value in asdict(await tend_conceptions(ctx)).items():
        ctx.count(f"conceptions_{key}", value)


PHASES = (Phase("divine_conceptions", divine_conceptions),)
