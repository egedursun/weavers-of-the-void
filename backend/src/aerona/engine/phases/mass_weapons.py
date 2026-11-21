from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mass_weapons.tend import tend_arsenals
from aerona.engine.phase import Phase


@reads(
    "table.battles",
    "table.deterrence_postures",
    "table.entities",
    "table.holder_custom_techniques",
    "table.holder_techniques",
    "table.mass_weapons",
    "table.nodes",
    "table.polity_profiles",
    "table.war_remnants",
    "table.war_sides",
    "table.wars",
)
@writes("table.applied_fixups", "table.deterrence_postures", "table.mass_weapons", "table.treaty_clauses", "table.treaty_profiles", "table.war_remnants")
async def mass_weapons(ctx: TickContext) -> None:
    for key, value in asdict(await tend_arsenals(ctx)).items():
        ctx.count(f"mass_weapons_{key}", value)


PHASES = (Phase("mass_weapons", mass_weapons),)
