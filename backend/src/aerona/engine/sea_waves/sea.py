from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.forecasting import ObservationMethodRow
from aerona.db.tables.sea_waves import WaveWarningRow
from aerona.db.tables.water import CoastRow
from aerona.domain.enums.folk_knowledge import FolkDomain
from aerona.domain.enums.water import CoastForm
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas

C = CoastForm
SHAPE_PCT = total(
    CoastForm,
    {C.CLIFF: 50, C.BEACH: 100, C.DELTA: 130, C.MARSH: 120, C.REEF: 60, C.ICE_SHELF: 40, C.FJORD: 150, C.LAGOON: 80},
)
WATCHING = (FolkDomain.WATERS, FolkDomain.LAND)


def sea_of(atlas: RegionAtlas, region_id: int) -> set[int]:
    start = [region_id] if atlas.is_water(region_id) else [other for other in atlas.neighbours(region_id) if atlas.is_water(other)]
    seen, frontier = set(start), list(start)
    while frontier:
        current = frontier.pop()
        for other in atlas.neighbours(current):
            if other not in seen and atlas.is_water(other):
                seen.add(other)
                frontier.append(other)
    return seen


def coasts_of(atlas: RegionAtlas, sea: set[int]) -> list[int]:
    return sorted({other for water in sea for other in atlas.neighbours(water) if not atlas.is_water(other)})


async def shape_pct(ctx: TickContext, region_id: int) -> int:
    coast = await ctx.session.get(CoastRow, region_id)
    return SHAPE_PCT[coast.form] if coast is not None else PERCENT


async def watched(ctx: TickContext, atlas: RegionAtlas, region_id: int) -> bool:
    floor = ctx.rules.sea_waves.observation_floor
    for community_id in atlas.communities_in(region_id):
        community = await ctx.session.get(EntityRow, community_id)
        people = await people_of(ctx.session, community) if community is not None else None
        if people is None:
            continue
        keen = (ObservationMethodRow.people_entity_id == people.id, ObservationMethodRow.domain.in_(WATCHING), ObservationMethodRow.accuracy >= floor)
        if await ctx.session.scalar(select(ObservationMethodRow.id).where(*keen).limit(1)) is not None:
            return True
    return False


async def warned(ctx: TickContext, atlas: RegionAtlas, region_id: int) -> bool:
    given = select(WaveWarningRow.id).where(WaveWarningRow.region_entity_id == region_id, WaveWarningRow.until_epoch >= ctx.epoch).limit(1)
    return await ctx.session.scalar(given) is not None or await watched(ctx, atlas, region_id)
