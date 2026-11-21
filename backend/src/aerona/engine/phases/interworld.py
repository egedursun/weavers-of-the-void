from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.interworld.tend import tend_interworld
from aerona.engine.phase import Phase


@reads(
    "settlement.population",
    "settlement.prosperity",
    "table.entities",
    "table.interworld_campaigns",
    "table.interworld_migrations",
    "table.journeys",
    "table.nodes",
    "table.occupations",
    "table.orbital_control",
    "table.routes",
    "table.war_sides",
    "table.wars",
)
@writes("table.interworld_campaigns", "table.interworld_migrations", "table.journeys", "table.network_outages", "table.orbital_control", "table.routes")
async def interworld(ctx: TickContext) -> None:
    for key, value in asdict(await tend_interworld(ctx)).items():
        ctx.count(f"interworld_{key}", value)


PHASES = (Phase("interworld", interworld),)
