from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.fertility_means.tend import tend_means
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "table.body_systems",
    "table.bonds",
    "table.entities",
    "table.fertility_means",
    "table.fertility_uses",
    "table.holder_levels",
    "table.intimacy_norms",
    "table.mortal_profiles",
    "table.node_births",
    "table.nodes",
    "table.polity_members",
    "table.population_instruments",
    "table.population_policies",
    "table.state_changes",
    "table.trade_route_profiles",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.fertility_means",
    "table.fertility_uses",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.mortal_profiles",
    "table.node_births",
)
async def fertility_means(ctx: TickContext) -> None:
    for key, value in asdict(await tend_means(ctx)).items():
        ctx.count(f"fertility_means_{key}", value)


PHASES = (Phase("fertility_means", fertility_means),)
