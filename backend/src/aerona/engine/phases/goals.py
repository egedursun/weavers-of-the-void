from aerona.engine.context import TickContext
from aerona.engine.gods.goals import epoch_end_goals
from aerona.engine.gods.queries import cosmos_row
from aerona.engine.phase import Phase


async def goals(ctx: TickContext) -> None:
    if await cosmos_row(ctx.session) is None:
        return
    await epoch_end_goals(ctx)


PHASES = (Phase("goals", goals),)
