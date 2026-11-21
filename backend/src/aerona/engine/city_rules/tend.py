from aerona.engine.city_rules import land, services
from aerona.engine.city_rules.book import CityTally
from aerona.engine.city_rules.conurbations import tend_conurbations
from aerona.engine.context import TickContext


async def tend_cities(ctx: TickContext) -> CityTally:
    tally = CityTally()
    await land.apply_legacy(ctx, tally)
    await services.apply_legacy(ctx, tally)
    await land.tend_rules(ctx, tally)
    await land.crowded_towns(ctx, tally)
    await services.tend_services(ctx, tally)
    await services.towns_found_services(ctx, tally)
    await tend_conurbations(ctx, tally)
    return tally
