from aerona.engine.context import TickContext
from aerona.engine.cosmos.formation import FormationTally, form_worlds
from aerona.engine.cycles.ecology import EcologyTally, keep_transformations
from aerona.engine.environment.long_seasons import SeasonTally, keep_seasons
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count
from aerona.engine.storyteller.ages import AgeTally, keep_ages
from aerona.engine.storyteller.arcs import ArcTally, detect, keep_arcs
from aerona.engine.storyteller.drama import DramaTally, keep_drama


@reads("table.formation_histories", "table.nodes", "table.star_physics", "table.world_physics", "table.worlds")
@writes("table.formation_histories", "table.impact_events")
async def formation_history(ctx: TickContext) -> None:
    tally = FormationTally()
    await form_worlds(ctx, tally)
    count(ctx, "formation", tally)


@reads("table.entities", "table.irregular_seasons", "table.natural_law_profiles", "table.nodes", "table.world_physics", "table.worlds")
async def long_seasons(ctx: TickContext) -> None:
    tally = SeasonTally()
    await keep_seasons(ctx, tally)
    count(ctx, "long_seasons", tally)


@reads("table.long_plans")
async def eco_transformations(ctx: TickContext) -> None:
    tally = EcologyTally()
    await keep_transformations(ctx, tally)
    count(ctx, "eco_transformations", tally)


@reads("table.cosmos")
async def ages(ctx: TickContext) -> None:
    tally = AgeTally()
    await keep_ages(ctx, tally)
    count(ctx, "ages", tally)


@reads(
    "table.age_echoes",
    "table.arc_beats",
    "table.arc_figures",
    "table.arcs",
    "table.bonds",
    "table.chronicle",
    "table.divinations",
    "table.dreams",
    "table.entities",
    "table.foresights",
    "table.house_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.legendary_quests",
    "table.mantlings",
    "table.mortal_profiles",
    "table.node_births",
    "table.nodes",
    "table.oaths",
    "table.office_history",
    "table.offices",
    "table.prophecy_conditions",
    "table.sentences",
    "table.setups",
    "table.thread_links",
    "table.threads",
    "table.traits",
)
@writes(
    "table.arc_beats",
    "table.arc_figures",
    "table.arcs",
    "table.chronicle",
    "table.chronicle_entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.setups",
)
async def arcs(ctx: TickContext) -> None:
    tally, drama = ArcTally(), DramaTally()
    moved = await keep_arcs(ctx, tally)
    await detect(ctx, tally)
    await keep_drama(ctx, moved, drama)
    count(ctx, "arcs", tally)
    count(ctx, "drama", drama)


PHASES = (
    Phase("formation_history", formation_history),
    Phase("long_seasons", long_seasons),
    Phase("eco_transformations", eco_transformations),
    Phase("ages", ages),
    Phase("arcs", arcs),
)
