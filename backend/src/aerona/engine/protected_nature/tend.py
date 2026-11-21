from aerona.engine.context import TickContext
from aerona.engine.protected_nature import areas
from aerona.engine.protected_nature.book import NatureTally
from aerona.engine.protected_nature.movement import tend_movements
from aerona.engine.protected_nature.species import tend_species


async def tend_nature(ctx: TickContext) -> NatureTally:
    tally = NatureTally()
    await areas.apply_legacy(ctx, tally)
    await areas.tend_areas(ctx, tally)
    await tend_species(ctx, tally)
    await tend_movements(ctx, tally)
    return tally
