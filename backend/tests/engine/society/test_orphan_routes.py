from aerona.domain.enums.economy import TradeRouteStatus
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.routes import RouteTally, close_orphan, load_routes, orphaned
from tests.engine.society.factories import Realm, chronicle_keys, context, settlement, trade_route


async def test_a_route_that_lost_a_market_closes_instead_of_crashing_the_trade_flow(realm: Realm) -> None:
    ctx = context(realm.session)
    first = await settlement(realm, "Harbourgate")
    second = await settlement(realm, "Saltmarsh")
    await trade_route(realm, first, second)
    (route,) = await load_routes(ctx)
    assert not orphaned(await EconomyBook.load(ctx), route)
    second.status, second.end_epoch = EntityStatus.DESTROYED, ctx.epoch
    await realm.session.flush()
    book = await EconomyBook.load(ctx)
    assert orphaned(book, route)
    tally = RouteTally()
    await close_orphan(ctx, route, tally)
    assert route.profile.status is TradeRouteStatus.CLOSED and tally.decayed == 1
    assert "trade_route.orphaned" in await chronicle_keys(realm.session)
    assert await load_routes(ctx) == []
