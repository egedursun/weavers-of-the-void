from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.protected_nature.tend import tend_nature


@reads(
    "settlement.prosperity",
    "table.applied_fixups",
    "table.conservation_movements",
    "table.game_reserves",
    "table.gardens",
    "table.movement_profiles",
    "table.node_births",
    "table.protected_areas",
    "table.region_environment",
    "table.settlement_profiles",
    "table.species_protections",
    "table.species_ranges",
)
@writes(
    "settlement.prosperity",
    "table.applied_fixups",
    "table.chronicle",
    "table.chronicle_entities",
    "table.conservation_movements",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.protected_areas",
    "table.region_environment",
    "table.settlement_profiles",
    "table.species_protections",
    "table.species_ranges",
)
async def protected_nature(ctx: TickContext) -> None:
    for key, value in asdict(await tend_nature(ctx)).items():
        ctx.count(f"protected_nature_{key}", value)


PHASES = (Phase("protected_nature", protected_nature),)
