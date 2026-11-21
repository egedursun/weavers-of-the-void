from aerona.engine.context import TickContext
from aerona.engine.mass_weapons.book import ArsenalTally
from aerona.engine.mass_weapons.deterrence import expose_bluffs
from aerona.engine.mass_weapons.limits import bind_arsenals
from aerona.engine.mass_weapons.programme import seek_arms, tend_programmes
from aerona.engine.mass_weapons.remnants import after_wars, tend_remnants


async def tend_arsenals(ctx: TickContext) -> ArsenalTally:
    tally = ArsenalTally()
    await seek_arms(ctx, tally)
    await tend_programmes(ctx, tally)
    await expose_bluffs(ctx, tally)
    await bind_arsenals(ctx, tally)
    await after_wars(ctx, tally)
    await tend_remnants(ctx, tally)
    return tally
