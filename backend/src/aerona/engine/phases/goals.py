from aerona.engine.context import TickContext
from aerona.engine.gods.goals import epoch_end_goals
from aerona.engine.gods.queries import cosmos_row
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "people.population",
    "table.achievements",
    "table.action_records",
    "table.bonds",
    "table.chronicle",
    "table.cosmos",
    "table.dimensional_events",
    "table.dimensions",
    "table.entities",
    "table.entity_flags",
    "table.foreign_gods",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.heroquests",
    "table.horizon_intuitions",
    "table.journeys",
    "table.legendary_quests",
    "table.mantlings",
    "table.messages",
    "table.miracle_records",
    "table.museum_collections",
    "table.nodes",
    "table.rifts",
    "table.routes",
    "table.scenarios",
    "table.scores",
    "table.sons",
    "table.stars",
    "table.war_sides",
    "table.wars",
    "table.worlds",
)
@writes("table.achievements", "table.notifications", "table.scores")
async def goals(ctx: TickContext) -> None:
    if await cosmos_row(ctx.session) is None:
        return
    await epoch_end_goals(ctx)


PHASES = (Phase("goals", goals),)
