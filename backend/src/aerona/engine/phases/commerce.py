from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.markets import MarketTally, apply_aggregate_prices, market_nodes, quote_market, raise_district, store_quotes
from aerona.engine.economy.money import MoneyTally, collect, lend
from aerona.engine.economy.routes import RouteTally, carry, contacts, controllers, enemies_of, found_route, load_routes, set_tolls, upkeep
from aerona.engine.economy.stocks import sync_aggregates
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.environment import works_by_region


@reads("people.population", "settlement.population", "table.community_societies", "table.community_stocks", "table.currencies", "table.workshops")
@writes("table.community_societies", "table.community_stocks", "table.goods_flows", "table.market_prices", "table.workshops")
async def markets(ctx: TickContext) -> None:
    book = await EconomyBook.load(ctx)
    tally = MarketTally()
    for community in book.communities:
        await raise_district(ctx, book, community, tally)
        quotes = await quote_market(ctx, book, community)
        await apply_aggregate_prices(book, community, quotes)
    for market in market_nodes(book):
        await store_quotes(ctx, market, await quote_market(ctx, book, market))
        tally.priced += 1
    ctx.count("districts", tally.districts)
    ctx.count("markets", tally.priced)


@reads(
    "faction.wealth",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "region.danger",
    "settlement.population",
    "settlement.prosperity",
    "trade_route.capacity",
    "trade_route.culture",
    "trade_route.danger",
    "trade_route.renown",
    "table.armies",
    "table.bonds",
    "table.community_societies",
    "table.community_stocks",
    "table.market_prices",
    "table.region_environment",
    "table.trade_route_profiles",
    "table.trade_route_regions",
    "table.trade_route_tolls",
    "table.workshops",
)
@writes(
    "faction.wealth",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "settlement.population",
    "settlement.prosperity",
    "trade_route.capacity",
    "trade_route.culture",
    "trade_route.danger",
    "trade_route.renown",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_societies",
    "table.community_stocks",
    "table.entities",
    "table.goods_flows",
    "table.incident_participants",
    "table.incidents",
    "table.market_prices",
    "table.trade_flows",
    "table.trade_route_profiles",
    "table.trade_route_regions",
    "table.trade_route_tolls",
    "table.wars",
)
async def trade_flow(ctx: TickContext) -> None:
    book = await EconomyBook.load(ctx)
    tally = RouteTally()
    works = await works_by_region(ctx, book.ground)
    nodes = market_nodes(book)
    routes = await load_routes(ctx)
    quotes = {market.id: await quote_market(ctx, book, market) for market in nodes}
    for first, second, path in await contacts(ctx, book, nodes, routes, quotes):
        routes.append(await found_route(ctx, book, first, second, path, works=works))
        tally.founded += 1
    masters = await controllers(ctx, book)
    enemies = await enemies_of(ctx)
    for route in routes:
        await set_tolls(ctx, book, route, masters)
        await carry(ctx, book, route, quotes, tally)
        await upkeep(ctx, book, route, works=works, enemies=enemies, tally=tally)
    for market in nodes:
        await sync_aggregates(ctx.session, ctx.rules, market)
    ctx.count("routes_founded", tally.founded)
    ctx.count("routes_opened", tally.opened)
    ctx.count("routes_decayed", tally.decayed)
    ctx.count("routes_blockaded", tally.blockaded)
    ctx.count("loads_moved", tally.moved)
    ctx.count("loads_lost", tally.lost)
    ctx.count("tolls", tally.tolls)
    ctx.count("shipwrecks", tally.shipwrecks)
    ctx.count("route_wars", tally.wars)


@reads("faction.wealth", "people.prosperity", "people.wealth", "settlement.prosperity", "table.bonds", "table.community_societies", "table.loans")
@writes(
    "faction.wealth",
    "people.prosperity",
    "people.wealth",
    "settlement.prosperity",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.incident_participants",
    "table.incidents",
    "table.loans",
    "table.memories",
)
async def banking(ctx: TickContext) -> None:
    book = await EconomyBook.load(ctx)
    tally = MoneyTally()
    await lend(ctx, book, tally)
    await collect(ctx, book, tally)
    ctx.count("loans", tally.lent)
    ctx.count("repaid", tally.repaid)
    ctx.count("defaults", tally.defaulted)
    ctx.count("collapses", tally.collapsed)


PHASES = (Phase("markets", markets), Phase("trade_flow", trade_flow), Phase("banking", banking))
