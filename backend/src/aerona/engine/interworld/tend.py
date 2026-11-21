from aerona.engine.context import TickContext
from aerona.engine.interworld.book import InterworldTally
from aerona.engine.interworld.campaigns import tend_campaigns
from aerona.engine.interworld.migrations import tend_migrations
from aerona.engine.interworld.orbit import tend_orbits


async def tend_interworld(ctx: TickContext) -> InterworldTally:
    tally = InterworldTally()
    await tend_campaigns(ctx, tally)
    await tend_orbits(ctx, tally)
    await tend_migrations(ctx, tally)
    return tally
