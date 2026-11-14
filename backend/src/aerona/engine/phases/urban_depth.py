from aerona.engine.context import TickContext
from aerona.engine.economy.convoys import ConvoyTally, run_convoys, wear_fleets
from aerona.engine.economy.manipulation import PlayTally, play_markets
from aerona.engine.factions.crime import CrimeTally, run_underworld
from aerona.engine.factions.mage_orders import OrderTally, keep_orders
from aerona.engine.factions.trading_posts import PostTally, keep_posts
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count
from aerona.engine.urban.coverage import CoverageTally, cover_towns
from aerona.engine.urban.desirability import DesirabilityTally, assess_towns
from aerona.engine.urban.housing import HousingTally, house_towns
from aerona.engine.urban.turf import TurfTally, hold_turf


@reads(
    "settlement.population", "table.district_services", "table.districts", "table.holder_levels", "table.settlement_infrastructure", "table.settlement_profiles"
)
@writes("table.district_services", "table.districts", "table.settlement_profiles")
async def district_coverage(ctx: TickContext) -> None:
    tally = CoverageTally()
    await cover_towns(ctx, tally)
    count(ctx, "coverage", tally)


@reads("settlement.population", "table.districts", "table.region_pollution", "table.settlement_infrastructure", "table.settlement_profiles")
@writes("table.districts")
async def desirability(ctx: TickContext) -> None:
    tally = DesirabilityTally()
    await assess_towns(ctx, tally)
    count(ctx, "desirability", tally)


@reads(
    "settlement.defense",
    "settlement.population",
    "table.community_societies",
    "table.district_services",
    "table.districts",
    "table.holder_levels",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.structure_profiles",
    "table.turf",
)
@writes("table.districts", "table.settlement_infrastructure", "table.settlement_profiles")
async def housing_evolution(ctx: TickContext) -> None:
    tally = HousingTally()
    await house_towns(ctx, tally)
    count(ctx, "housing", tally)


@reads("table.turf")
async def turf(ctx: TickContext) -> None:
    tally = TurfTally()
    await hold_turf(ctx, tally)
    count(ctx, "turf", tally)


@reads("table.crime_stances")
async def crime_orgs(ctx: TickContext) -> None:
    tally = CrimeTally()
    await run_underworld(ctx, tally)
    count(ctx, "underworld", tally)


@reads("table.bonds", "table.polity_members", "table.trading_posts")
async def trading_posts(ctx: TickContext) -> None:
    tally = PostTally()
    await keep_posts(ctx, tally)
    count(ctx, "trading_post", tally)


@reads("table.bonds", "table.law_jurisdictions", "table.law_profiles", "table.polity_members")
async def magical_orders(ctx: TickContext) -> None:
    tally = OrderTally()
    await keep_orders(ctx, tally)
    count(ctx, "order", tally)


@reads(
    "settlement.defense",
    "settlement.population",
    "table.community_cohorts",
    "table.convoys",
    "table.disease_cures",
    "table.disease_profiles",
    "table.endemic_diseases",
    "table.herds",
    "table.holder_techniques",
    "table.immunities",
    "table.ley_lines",
    "table.outbreaks",
    "table.plague_responses",
    "table.quarantines",
    "table.species_hosts",
    "table.species_profiles",
    "table.species_ranges",
    "table.trade_flows",
    "table.transport_fleets",
    "table.vehicle_groups",
    "trade_route.capacity",
)
@writes("table.convoys", "table.transport_fleets")
async def convoys(ctx: TickContext) -> None:
    tally = ConvoyTally()
    await run_convoys(ctx, tally)
    count(ctx, "convoy", tally)


@reads("settlement.wealth", "table.polity_members", "table.polity_profiles", "table.transport_fleets")
@writes("table.transport_fleets")
async def transport_fleets(ctx: TickContext) -> None:
    tally = ConvoyTally()
    await wear_fleets(ctx, tally)
    count(ctx, "fleet", tally)


@reads("table.community_stocks", "table.market_plays", "table.trading_posts")
async def market_manipulation(ctx: TickContext) -> None:
    tally = PlayTally()
    await play_markets(ctx, tally)
    count(ctx, "market_play", tally)


PHASES = (
    Phase("district_coverage", district_coverage),
    Phase("desirability", desirability),
    Phase("housing_evolution", housing_evolution),
    Phase("turf", turf),
    Phase("crime_orgs", crime_orgs),
    Phase("trading_posts", trading_posts),
    Phase("magical_orders", magical_orders),
    Phase("convoys", convoys),
    Phase("transport_fleets", transport_fleets),
    Phase("market_manipulation", market_manipulation),
)
