from aerona.engine.context import TickContext
from aerona.engine.cosmos.world_ends import EndingTally, keep_world_ends
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lifecycle.ends import EndTally, keep_ends
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads(
    "table.breach_points",
    "table.castings",
    "table.endemic_diseases",
    "table.entities",
    "table.ideology_adherents",
    "table.ideology_profiles",
    "table.lab_texts",
    "table.lifecycle_states",
    "table.outbreaks",
    "table.rite_profiles",
    "table.species_hosts",
    "table.theory_adherents",
    "table.theory_profiles",
    "table.worlds",
)
@writes(
    "table.breach_points",
    "table.chronicle",
    "table.chronicle_entities",
    "table.ideology_adherents",
    "table.lifecycle_states",
    "table.rite_profiles",
    "table.theory_adherents",
)
async def lifecycle_ends(ctx: TickContext) -> None:
    tally = EndTally()
    await keep_ends(ctx, tally)
    count(ctx, "lifecycle_ends", tally)


@reads("table.sky_events", "table.stars", "table.world_ends", "table.world_type_profiles", "table.worlds")
@writes("table.chronicle", "table.entities", "table.world_ends")
async def world_ends(ctx: TickContext) -> None:
    tally = EndingTally()
    await keep_world_ends(ctx, tally)
    count(ctx, "world_ends", tally)


PHASES = (Phase("lifecycle_ends", lifecycle_ends), Phase("world_ends", world_ends))
