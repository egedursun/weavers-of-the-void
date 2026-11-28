from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.creature_groups.groups import tend_groups
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "settlement.population",
    "settlement.prosperity",
    "species.intelligence",
    "table.beast_profiles",
    "table.creature_groups",
    "table.entities",
    "table.entity_traits",
    "table.node_births",
    "table.protected_areas",
    "table.species_ranges",
    "table.state_changes",
)
@writes(
    "settlement.prosperity",
    "table.chronicle",
    "table.chronicle_entities",
    "table.creature_groups",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.node_births",
    "table.species_ranges",
)
async def creature_groups(ctx: TickContext) -> None:
    for key, value in asdict(await tend_groups(ctx)).items():
        ctx.count(f"creature_groups_{key}", value)


PHASES = (Phase("creature_groups", creature_groups),)
