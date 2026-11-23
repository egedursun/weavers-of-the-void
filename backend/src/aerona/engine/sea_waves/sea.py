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
    {
        C.CLIFF: 50,
        C.BEACH: 100,
        C.DELTA: 130,
        C.MARSH: 120,
        C.REEF: 60,
        C.ICE_SHELF: 40,
        C.FJORD: 150,
        C.LAGOON: 80,
        C.ESTUARY: 140,
        C.MANGROVE: 40,
        C.BARRIER_ISLAND: 60,
    },
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


async def open_coast(ctx: TickContext, atlas: RegionAtlas, region_id: int) -> tuple[int | None, list[int]]:
    water = sea_of(atlas, region_id)
    if water:
        return min(water), coasts_of(atlas, water)
    coastal = set(await ctx.session.scalars(select(CoastRow.region_entity_id)))
    world = atlas.world_of(region_id)
    if region_id not in coastal or world is None:
        return None, []
    return None, sorted(coast for coast in coastal if atlas.world_of(coast) == world)


async def shape_pct(ctx: TickContext, region_id: int) -> int:
    coast = await ctx.session.get(CoastRow, region_id)
    return SHAPE_PCT[coast.form] if coast is not None else PERCENT


async def watcher(ctx: TickContext, atlas: RegionAtlas, region_id: int) -> ObservationMethodRow | None:
    floor = ctx.rules.sea_waves.observation_floor
    for community_id in atlas.communities_in(region_id):
        community = await ctx.session.get(EntityRow, community_id)
        people = await people_of(ctx.session, community) if community is not None else None
        if people is None:
            continue
        keen = (ObservationMethodRow.people_entity_id == people.id, ObservationMethodRow.domain.in_(WATCHING), ObservationMethodRow.accuracy >= floor)
        found = await ctx.session.scalar(
            select(ObservationMethodRow).where(*keen).order_by(ObservationMethodRow.accuracy.desc(), ObservationMethodRow.id).limit(1)
        )
        if found is not None:
            return found
    return None


async def warned(ctx: TickContext, atlas: RegionAtlas, region_id: int) -> bool:
    given = select(WaveWarningRow.id).where(WaveWarningRow.region_entity_id == region_id, WaveWarningRow.until_epoch >= ctx.epoch).limit(1)
    if await ctx.session.scalar(given) is not None:
        return True
    seen = await watcher(ctx, atlas, region_id)
    if seen is None:
        return False
    until = ctx.epoch + ctx.rules.sea_waves.warning_epochs
    ctx.session.add(
        WaveWarningRow(region_entity_id=region_id, method=seen.method, by_node_id=seen.people_entity_id, epoch=ctx.epoch, until_epoch=until, locked=[])
    )
    return True
