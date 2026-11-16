from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.orders.economy import OrderTally, keep_economy
from aerona.engine.orders.exchange import ExchangeTally, keep_exchange
from aerona.engine.orders.putting_out import PuttingOutTally, keep_putting_out
from aerona.engine.orders.savings import SavingTally, keep_savings
from aerona.engine.orders.tourism import TourismTally, keep_tourism
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count


@reads(
    "table.hoards",
    "table.households",
    "table.mind_attributes",
    "table.polity_members",
    "table.polity_profiles",
    "table.savings",
    "table.settlement_profiles",
    "table.wars",
)
@writes("table.hoards", "table.households", "table.savings", "table.settlement_profiles")
async def saving(ctx: TickContext) -> None:
    tally = SavingTally()
    await keep_savings(ctx, tally)
    count(ctx, "saving", tally)


@reads(
    "table.bills_of_exchange",
    "table.community_societies",
    "table.currencies",
    "table.exchange_rates",
    "table.goods_flows",
    "table.loans",
    "table.polity_members",
    "table.trade_route_profiles",
)
@writes("table.bills_of_exchange", "table.exchange_rates", "table.loans")
async def money_changing(ctx: TickContext) -> None:
    tally = ExchangeTally()
    await keep_exchange(ctx, tally)
    count(ctx, "money_changing", tally)


@reads(
    "table.bonds",
    "table.community_societies",
    "table.economic_order_kinds",
    "table.economic_orders",
    "table.holder_levels",
    "table.law_jurisdictions",
    "table.offices",
    "table.order_transitions",
    "table.polity_members",
    "table.polity_profiles",
    "table.structure_profiles",
)
@writes("table.bonds", "table.community_societies", "table.economic_order_kinds", "table.economic_orders", "table.order_transitions")
async def economic_orders(ctx: TickContext) -> None:
    tally = OrderTally()
    await keep_economy(ctx, tally)
    count(ctx, "economic_orders", tally)


@reads("table.chain_holdings", "table.community_stocks", "table.production_runs", "table.putting_out", "table.trade_route_profiles")
@writes("table.chain_holdings", "table.community_stocks", "table.putting_out")
async def putting_out(ctx: TickContext) -> None:
    tally = PuttingOutTally()
    await keep_putting_out(ctx, tally)
    count(ctx, "putting_out", tally)


@reads(
    "settlement.population",
    "settlement.prosperity",
    "table.battlefield_features",
    "table.community_cohorts",
    "table.disease_cures",
    "table.disease_profiles",
    "table.endemic_diseases",
    "table.herds",
    "table.holder_techniques",
    "table.immunities",
    "table.impurity_sources",
    "table.ley_lines",
    "table.outbreaks",
    "table.plague_responses",
    "table.quarantines",
    "table.settlement_profiles",
    "table.species_hosts",
    "table.species_profiles",
    "table.species_ranges",
    "table.structure_profiles",
    "table.tourist_flows",
)
@writes("table.tourist_flows")
async def tourism(ctx: TickContext) -> None:
    tally = TourismTally()
    await keep_tourism(ctx, tally)
    count(ctx, "tourism", tally)


PHASES = (
    Phase("saving", saving),
    Phase("money_changing", money_changing),
    Phase("economic_orders", economic_orders),
    Phase("putting_out", putting_out),
    Phase("tourism", tourism),
)
