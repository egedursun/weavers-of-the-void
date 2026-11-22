from dataclasses import asdict

from aerona.engine.context import TickContext
from aerona.engine.feeling_spread.moods import tend_moods
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "mortal.charisma",
    "table.creator",
    "table.crowd_moods",
    "table.dimensions",
    "table.entities",
    "table.feeling_spread",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.household_members",
    "table.mind_facets",
    "table.minds",
    "table.node_births",
    "table.nodes",
    "table.sons",
    "table.stars",
    "table.thoughts",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.crowd_moods",
    "table.feeling_spread",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.thoughts",
)
async def feeling_spread(ctx: TickContext) -> None:
    for key, value in asdict(await tend_moods(ctx)).items():
        ctx.count(f"feeling_spread_{key}", value)


PHASES = (Phase("feeling_spread", feeling_spread),)
