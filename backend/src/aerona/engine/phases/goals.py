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
    "table.horizon_intuitions",
    "table.journeys",
    "table.legendary_quests",
    "table.nodes",
    "table.scenarios",
    "table.scores",
    "table.war_sides",
    "table.wars",
)
@writes("table.achievements", "table.notifications", "table.scores")
async def goals(ctx: TickContext) -> None:
    if await cosmos_row(ctx.session) is None:
        return
    await epoch_end_goals(ctx)


PHASES = (Phase("goals", goals),)
