from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.kinds.trade_modes import TRADE_MODES
from aerona.catalog.terrain import terrain_has
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.economy import TradeMode
from aerona.domain.enums.environment import TerrainTrait
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.renames import rename_everywhere

MODE_KEY = "mode"


async def over_water(session: AsyncSession, atlas: RegionAtlas, profile: TradeRouteProfileRow) -> bool:
    regions = {atlas.top_region(market) for market in (profile.first_market_id, profile.second_market_id)}
    if None in regions:
        return False
    grounds = [await session.get(RegionEnvironmentRow, region) for region in sorted(region for region in regions if region is not None)]
    return all(ground is not None and terrain_has(ground.dominant_terrain, TerrainTrait.WATERY) for ground in grounds)


async def roads_over_water(session: AsyncSession) -> list[int]:
    atlas = await RegionAtlas.load(session)
    found: list[int] = []
    for profile in await session.scalars(
        select(TradeRouteProfileRow).where(TradeRouteProfileRow.mode == TradeMode.ROAD).order_by(TradeRouteProfileRow.route_entity_id)
    ):
        if MODE_KEY not in (profile.locked or []) and await over_water(session, atlas, profile):
            found.append(profile.route_entity_id)
    return found


async def sail_road(session: AsyncSession, key: int) -> None:
    profile = await session.get(TradeRouteProfileRow, key)
    route = await session.get(EntityRow, key)
    if profile is None or route is None:
        return
    profile.mode = TradeMode.SEA
    road = f"{TRADE_MODES[TradeMode.ROAD].words} of "
    if route.name.startswith(road):
        await rename_everywhere(session, key, f"{TRADE_MODES[TradeMode.SEA].words} of {route.name.removeprefix(road)}", free=True)
