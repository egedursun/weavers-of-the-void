from aerona.engine.commerce.seed import seed_commerce
from aerona.engine.commerce.trade import keep_commerce
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


@reads(
    "settlement.wealth",
    "table.applied_fixups",
    "table.brands",
    "table.creator",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.leases",
    "table.market_prices",
    "table.mortal_profiles",
    "table.node_births",
    "table.nodes",
    "table.polity_members",
    "table.promotions",
    "table.settlement_profiles",
    "table.shop_goods",
    "table.shops",
    "table.sons",
    "table.stars",
    "table.supply_tiers",
    "table.trade_route_profiles",
    "table.workshops",
    "table.worlds",
)
@writes(
    "settlement.prosperity",
    "settlement.wealth",
    "table.applied_fixups",
    "table.brands",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.leases",
    "table.loans",
    "table.mortal_profiles",
    "table.polity_profiles",
    "table.promotions",
    "table.settlement_profiles",
    "table.shop_goods",
    "table.shops",
    "table.supply_tiers",
)
async def commerce_practice(ctx: TickContext) -> None:
    seeded = await seed_commerce(ctx)
    ctx.count("commerce_seeded_tiers", seeded.tiers)
    ctx.count("commerce_seeded_shops", seeded.shops)
    ctx.count("commerce_freed_common_tiers", seeded.freed)
    tally = await keep_commerce(ctx)
    ctx.count("commerce_sold", tally.sold)
    ctx.count("commerce_closed", tally.closed)
    ctx.count("commerce_tier_income", tally.tier_income)
    ctx.count("commerce_cornered", tally.cornered)
    ctx.count("commerce_promoted", tally.promoted)
    ctx.count("commerce_exposed", tally.exposed)
    ctx.count("commerce_rent_paid", tally.rent_paid)
    ctx.count("commerce_defaulted", tally.defaulted)
    ctx.count("commerce_leases_ended", tally.leases_ended)


PHASES = (Phase("commerce_practice", commerce_practice),)
