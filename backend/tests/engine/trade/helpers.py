from aerona.db.tables.economy import TradeRouteProfileRow, TradeRouteRegionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import WorldSeasonRow
from aerona.domain.enums.economy import TradeMode, TradeRouteStatus
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import TradeRouteStats
from aerona.engine.economy.routes import Route
from tests.engine.society.factories import Realm, make, settlement


async def lay_route(realm: Realm, *, mode: TradeMode = TradeMode.ROAD, status: TradeRouteStatus = TradeRouteStatus.OPEN) -> Route:
    first = await settlement(realm, "Brennhold")
    second = await settlement(realm, "Ashwick", location_id=realm.far_region.id)
    entity = await make(
        realm.session,
        "Dust Road",
        EntityType.TRADE_ROUTE,
        TradeRouteStats(capacity=100, danger=10, renown=0, culture=0),
        world_id=realm.world.id,
        location_id=realm.region.id,
    )
    profile = TradeRouteProfileRow(
        route_entity_id=entity.id,
        first_market_id=first.id,
        second_market_id=second.id,
        mode=mode,
        status=status,
        length=2,
        founded_epoch=1,
        last_traffic_epoch=2,
        locked=[],
    )
    realm.session.add(profile)
    path = [realm.region.id, realm.far_region.id]
    for position, region in enumerate(path):
        realm.session.add(TradeRouteRegionRow(route_entity_id=entity.id, position=position, region_entity_id=region))
    await realm.session.flush()
    return Route(entity, profile, path)


async def seasons_of(realm: Realm, *names: str) -> list[WorldSeasonRow]:
    rows = [
        WorldSeasonRow(
            world_id=realm.world.id, position=index, name=name, temperature_shift=-10 * index, rain_shift=5 * index, growth=50, travel=80, campaign=50
        )
        for index, name in enumerate(names)
    ]
    realm.session.add_all(rows)
    await realm.session.flush()
    return rows


async def market(realm: Realm, route: Route, end: int) -> EntityRow:
    found = await realm.session.get(EntityRow, route.ends[end])
    assert found is not None
    return found
