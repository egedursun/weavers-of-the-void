from aerona.db.write_guard import held, unheld
from aerona.domain.enums.region import DangerHarm
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.chokepoints import route_grants
from aerona.engine.economy.markets import MarketTally, apply_aggregate_prices, market_nodes, quote_market, raise_district, store_quotes
from aerona.engine.economy.money import MoneyTally, collect, lend
from aerona.engine.economy.realm_credit import collect_from_realms, lend_to_realms
from aerona.engine.economy.route_backfill import route_backfill
from aerona.engine.economy.route_dangers import Lairs
from aerona.engine.economy.routes import (
    RouteTally,
    assess,
    carry,
    close_orphan,
    contacts,
    controllers,
    enemies_of,
    found_route,
    load_routes,
    orphaned,
    set_tolls,
    upkeep,
)
from aerona.engine.economy.stocks import sync_aggregates
from aerona.engine.economy.toll_polities import Realms
from aerona.engine.environment.dangers import weighted_dangers
from aerona.engine.environment.works import works_by_region
from aerona.engine.factions.book import robber_ids
from aerona.engine.finance.policy import PolicyBook
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "people.population",
    "people.prosperity",
    "settlement.population",
    "settlement.prosperity",
    "table.army_profiles",
    "table.bonds",
    "table.calendars",
    "table.community_industry",
    "table.community_labour",
    "table.community_methods",
    "table.community_societies",
    "table.community_stocks",
    "table.cult_tenets",
    "table.currencies",
    "table.epoch_year_cursors",
    "table.faction_profiles",
    "table.forced_weather",
    "table.goods_flows",
    "table.holder_levels",
    "table.holder_techniques",
    "table.law_jurisdictions",
    "table.market_plays",
    "table.market_price_holds",
    "table.market_prices",
    "table.people_biology",
    "table.people_culture",
    "table.place_environment",
    "table.plague_responses",
    "table.plant_profiles",
    "table.polity_members",
    "table.preferences",
    "table.region_crops",
    "table.region_environment",
    "table.region_pollution",
    "table.resource_profiles",
    "table.resource_workers",
    "table.skills",
    "table.sky_events",
    "table.species_profiles",
    "table.species_yields",
    "table.tradition_profiles",
    "table.treaty_parties",
    "table.workshop_designs",
    "table.workshops",
    "table.world_biochemistries",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_societies",
    "table.community_stocks",
    "table.epoch_year_cursors",
    "table.goods_flows",
    "table.incident_participants",
    "table.incidents",
    "table.market_prices",
    "table.workshops",
)
async def markets(ctx: TickContext) -> None:
    book = await EconomyBook.load(ctx)
    tally = MarketTally()
    for community in unheld(book.communities):
        await raise_district(ctx, book, community, tally)
        quotes = await quote_market(ctx, book, community)
        await apply_aggregate_prices(book, community, quotes)
    for market in unheld(market_nodes(book)):
        await store_quotes(ctx, market, await quote_market(ctx, book, market))
        tally.priced += 1
    ctx.count("districts", tally.districts)
    ctx.count("markets", tally.priced)


@reads(
    "beast.danger",
    "faction.wealth",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "region.danger",
    "settlement.population",
    "settlement.prosperity",
    "settlement.wealth",
    "table.applied_fixups",
    "table.armies",
    "table.army_profiles",
    "table.beast_profiles",
    "table.beliefs",
    "table.bills_of_exchange",
    "table.bonds",
    "table.border_controls",
    "table.calendars",
    "table.community_industry",
    "table.community_labour",
    "table.community_methods",
    "table.community_societies",
    "table.community_stocks",
    "table.container_stocks",
    "table.convoys",
    "table.cult_tenets",
    "table.districts",
    "table.divine_wounds",
    "table.epoch_year_cursors",
    "table.faction_profiles",
    "table.forced_weather",
    "table.goods_flows",
    "table.holder_levels",
    "table.holder_techniques",
    "table.impurity_sources",
    "table.language_registers",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.market_plays",
    "table.market_price_holds",
    "table.market_prices",
    "table.measure_standards",
    "table.name_registry",
    "table.nodes",
    "table.number_systems",
    "table.people_biology",
    "table.people_culture",
    "table.place_environment",
    "table.plague_responses",
    "table.plant_profiles",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.preferences",
    "table.region_crops",
    "table.region_dangers",
    "table.region_environment",
    "table.region_pollution",
    "table.resource_profiles",
    "table.resource_workers",
    "table.sense_profiles",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.skills",
    "table.sky_events",
    "table.speaker_cohorts",
    "table.species_profiles",
    "table.species_yields",
    "table.trade_flows",
    "table.trade_policies",
    "table.trade_route_profiles",
    "table.trade_route_regions",
    "table.trade_route_tolls",
    "table.tradition_profiles",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.war_aims",
    "table.war_sides",
    "table.wars",
    "table.workshop_designs",
    "table.workshops",
    "table.world_biochemistries",
    "table.world_domain_hooks",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
    "trade_route.capacity",
    "trade_route.culture",
    "trade_route.danger",
    "trade_route.renown",
)
@writes(
    "faction.wealth",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "settlement.population",
    "settlement.prosperity",
    "table.applied_fixups",
    "table.beast_profiles",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_industry",
    "table.community_societies",
    "table.community_stocks",
    "table.entities",
    "table.epoch_year_cursors",
    "table.faction_profiles",
    "table.goods_flows",
    "table.incident_participants",
    "table.incidents",
    "table.market_prices",
    "table.name_registry",
    "table.polity_profiles",
    "table.polity_treasury",
    "table.settlement_profiles",
    "table.settlement_treasury",
    "table.trade_flows",
    "table.trade_route_losses",
    "table.trade_route_profiles",
    "table.trade_route_regions",
    "table.trade_route_tolls",
    "table.war_aims",
    "table.wars",
    "trade_route.capacity",
    "trade_route.culture",
    "trade_route.danger",
    "trade_route.renown",
)
async def trade_flow(ctx: TickContext) -> None:
    book = await EconomyBook.load(ctx)
    book.merchant_danger = await weighted_dangers(ctx.session, ctx.rules, DangerHarm.MERCHANTS)
    book.robbers = await robber_ids(ctx.session)
    tally = RouteTally()
    works = await works_by_region(ctx, book.ground)
    nodes = market_nodes(book)
    realms = await Realms.load(ctx.session)
    for key, value in (await route_backfill(ctx, realms)).items():
        ctx.count(f"backfilled_{key}", value)
    routes = await load_routes(ctx)
    quotes = {market.id: await quote_market(ctx, book, market) for market in nodes}
    policies = await PolicyBook.load(ctx, book)
    for first, second, path in await contacts(ctx, book, nodes, routes, quotes):
        if held(first.id, second.id):
            continue
        routes.append(await found_route(ctx, book, first, second, path, works=works))
        tally.founded += 1
    masters = await controllers(ctx, book, realms)
    grants = await route_grants(ctx.session)
    enemies = await enemies_of(ctx)
    lairs = await Lairs.load(ctx, book)
    for route in routes:
        if orphaned(book, route):
            await close_orphan(ctx, route, tally)
            continue
        tally.dangers[route.entity.id] = assess(ctx, book, route, lairs)
        await set_tolls(ctx, book, route, masters, realms=realms, grants=grants)
        await carry(ctx, book, route, quotes, tally, policies=policies)
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
    ctx.count("polity_tolls", tally.polity_tolls)
    ctx.count("beast_losses", tally.beast_losses)
    ctx.count("weather_losses", tally.weather_losses)
    ctx.count("chokepoints", tally.chokepoints)


@reads(
    "faction.wealth",
    "people.prosperity",
    "people.wealth",
    "settlement.prosperity",
    "table.army_profiles",
    "table.bonds",
    "table.calendars",
    "table.captives",
    "table.community_cohorts",
    "table.community_industry",
    "table.community_labour",
    "table.community_methods",
    "table.community_societies",
    "table.credit_profiles",
    "table.currencies",
    "table.forced_weather",
    "table.holder_levels",
    "table.holder_techniques",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.loans",
    "table.offices",
    "table.place_environment",
    "table.plague_responses",
    "table.plant_profiles",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.region_crops",
    "table.region_environment",
    "table.region_pollution",
    "table.resource_profiles",
    "table.resource_workers",
    "table.settlement_profiles",
    "table.skills",
    "table.sky_events",
    "table.species_profiles",
    "table.species_yields",
    "table.treaty_parties",
    "table.vassalages",
    "table.workshop_designs",
    "table.workshops",
    "table.world_biochemistries",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
)
@writes(
    "faction.wealth",
    "people.prosperity",
    "people.wealth",
    "settlement.prosperity",
    "table.bonds",
    "table.captives",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_cohorts",
    "table.community_relations",
    "table.community_societies",
    "table.credit_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.loans",
    "table.memories",
    "table.polity_profiles",
    "table.polity_treasury",
    "table.settlement_profiles",
)
async def banking(ctx: TickContext) -> None:
    book = await EconomyBook.load(ctx)
    tally = MoneyTally()
    await lend(ctx, book, tally)
    await lend_to_realms(ctx, book, tally)
    await collect(ctx, book, tally)
    await collect_from_realms(ctx, book, tally)
    ctx.count("loans", tally.lent)
    ctx.count("repaid", tally.repaid)
    ctx.count("defaults", tally.defaulted)
    ctx.count("collapses", tally.collapsed)


PHASES = (Phase("markets", markets), Phase("trade_flow", trade_flow), Phase("banking", banking))
