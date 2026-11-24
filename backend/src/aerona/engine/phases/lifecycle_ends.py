from aerona.engine.context import TickContext
from aerona.engine.cosmos.world_ends import EndingTally, keep_world_ends
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lifecycle.affairs import AffairTally, close_affairs
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
    "table.node_births",
    "table.nodes",
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
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.lifecycle_states",
    "table.rite_profiles",
    "table.theory_adherents",
)
async def lifecycle_ends(ctx: TickContext) -> None:
    tally = EndTally()
    await keep_ends(ctx, tally)
    count(ctx, "lifecycle_ends", tally)


@reads(
    "table.entities",
    "table.mass_weapons",
    "table.nodes",
    "table.outer_being_profiles",
    "table.replicator_lines",
    "table.replicator_presence",
    "table.rifts",
    "table.sky_events",
    "table.stars",
    "table.world_cycles",
    "table.world_ends",
    "table.world_type_profiles",
    "table.worlds",
)
@writes("table.chronicle", "table.entities", "table.world_ends")
async def world_ends(ctx: TickContext) -> None:
    tally = EndingTally()
    await keep_world_ends(ctx, tally)
    count(ctx, "world_ends", tally)


@reads(
    "table.bonds",
    "table.creator",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.gatherings",
    "table.gifts",
    "table.hero_quests",
    "table.incidents",
    "table.incubating_ideas",
    "table.mandates",
    "table.messages",
    "table.node_births",
    "table.nodes",
    "table.sons",
    "table.stars",
    "table.worlds",
)
@writes(
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.gifts",
    "table.hero_quests",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.incubating_ideas",
    "table.mandates",
)
async def affairs_of_the_ended(ctx: TickContext) -> None:
    closed = AffairTally()
    await close_affairs(ctx, closed)
    ctx.count("affairs_closed", closed.affairs)
    ctx.count("ties_closed", closed.ties)


PHASES = (Phase("lifecycle_ends", lifecycle_ends), Phase("world_ends", world_ends), Phase("affairs_of_the_ended", affairs_of_the_ended))
