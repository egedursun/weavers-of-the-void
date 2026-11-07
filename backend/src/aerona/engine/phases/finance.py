from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.finance.credit import CreditTally, tend_credit
from aerona.engine.finance.indicators import IndicatorTally, record_indicators
from aerona.engine.finance.policy import PolicyBook, PolicyTally, tend_policies
from aerona.engine.finance.speculation import SpeculationTally, tend_speculation
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "table.army_profiles",
    "table.beliefs",
    "table.bonds",
    "table.calendars",
    "table.community_industry",
    "table.community_labour",
    "table.community_methods",
    "table.community_societies",
    "table.faction_profiles",
    "table.forced_weather",
    "table.holder_levels",
    "table.holder_techniques",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.market_prices",
    "table.place_environment",
    "table.polity_members",
    "table.polity_profiles",
    "table.pressures",
    "table.production_runs",
    "table.region_environment",
    "table.region_pollution",
    "table.resource_profiles",
    "table.resource_workers",
    "table.skills",
    "table.sky_events",
    "table.trade_policies",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.war_sides",
    "table.wars",
    "table.workshop_designs",
    "table.workshops",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
)
@writes("table.trade_policies")
async def trade_policy(ctx: TickContext) -> None:
    book = await EconomyBook.load(ctx)
    tally = PolicyTally()
    await tend_policies(ctx, book, await PolicyBook.load(ctx, book), tally)
    await ctx.session.flush()
    ctx.count("policies_laid", tally.laid)
    ctx.count("policies_lifted", tally.lifted)


@reads(
    "table.community_societies",
    "table.community_stocks",
    "table.credit_profiles",
    "table.cult_doctrines",
    "table.currencies",
    "table.faction_profiles",
    "table.loans",
    "table.polity_profiles",
)
@writes("table.credit_profiles", "table.currencies", "table.war_sides", "table.wars")
async def credit_ratings(ctx: TickContext) -> None:
    tally = CreditTally()
    await tend_credit(ctx, tally)
    await ctx.session.flush()
    ctx.count("rated", tally.rated)
    ctx.count("strained", tally.strained)
    ctx.count("restructuring", tally.restructured)
    ctx.count("coins_backed", tally.backed)


@reads(
    "table.army_profiles",
    "table.bonds",
    "table.calendars",
    "table.community_industry",
    "table.community_labour",
    "table.community_methods",
    "table.community_societies",
    "table.faction_profiles",
    "table.forced_weather",
    "table.holder_levels",
    "table.holder_techniques",
    "table.market_prices",
    "table.mind_facets",
    "table.place_environment",
    "table.pressures",
    "table.region_environment",
    "table.region_pollution",
    "table.resource_profiles",
    "table.resource_workers",
    "table.skills",
    "table.sky_events",
    "table.speculations",
    "table.treaty_parties",
    "table.workshop_designs",
    "table.workshops",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
)
@writes(
    "table.community_stocks",
    "table.faction_profiles",
    "table.goods_flows",
    "table.memories",
    "table.mortal_profiles",
    "table.settlement_profiles",
    "table.speculations",
)
async def speculation(ctx: TickContext) -> None:
    book = await EconomyBook.load(ctx)
    tally = SpeculationTally()
    await tend_speculation(ctx, book, tally)
    await ctx.session.flush()
    ctx.count("hoards_opened", tally.opened)
    ctx.count("hoards_sold", tally.sold)
    ctx.count("busts", tally.busts)
    ctx.count("famine_hoards", tally.famine_hoards)


@reads(
    "table.army_profiles",
    "table.bonds",
    "table.calendars",
    "table.community_industry",
    "table.community_labour",
    "table.community_methods",
    "table.community_societies",
    "table.economic_indicators",
    "table.forced_weather",
    "table.holder_levels",
    "table.holder_techniques",
    "table.loans",
    "table.market_prices",
    "table.place_environment",
    "table.polity_members",
    "table.polity_profiles",
    "table.production_runs",
    "table.region_environment",
    "table.region_pollution",
    "table.resource_profiles",
    "table.resource_workers",
    "table.settlement_profiles",
    "table.skills",
    "table.sky_events",
    "table.trade_flows",
    "table.treaty_parties",
    "table.workshop_designs",
    "table.workshops",
    "table.world_maps",
    "table.world_materials",
    "table.world_seasons",
)
@writes("table.economic_indicators")
async def economic_indicators(ctx: TickContext) -> None:
    book = await EconomyBook.load(ctx)
    tally = IndicatorTally()
    await record_indicators(ctx, book, tally)
    await ctx.session.flush()
    ctx.count("indicators", tally.recorded)


PHASES = (
    Phase("trade_policy", trade_policy),
    Phase("credit_ratings", credit_ratings),
    Phase("speculation", speculation),
    Phase("economic_indicators", economic_indicators),
)
