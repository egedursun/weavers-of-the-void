from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.commodities import COMMODITIES
from aerona.catalog.finance import LUXURIES as LUXURY_GOODS
from aerona.catalog.finance import STAPLES
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.economy import CurrencyRow, MarketPriceHoldRow, MarketPriceRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, WorkshopKind
from aerona.domain.enums.environment import WeatherEffect
from aerona.domain.enums.industry import QualityTier
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import Commodity, KnowledgeBranch, SocialClass
from aerona.engine.context import TickContext
from aerona.engine.demography.basket import staples_of
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.good_kinds import good_book
from aerona.engine.economy.household import diet_demand
from aerona.engine.economy.manipulation import plays_at
from aerona.engine.economy.materials import price_premium
from aerona.engine.economy.stocks import epoch_need, goods_of, holding, lots_of, nourishment_need
from aerona.engine.environment.years import world_years
from aerona.engine.factions.book import monopoly_factor
from aerona.engine.faith.book import forbidden_foods
from aerona.engine.industry.quality import at_least, premium
from aerona.engine.lore.traditions import resent_taboo, taboos
from aerona.engine.mind.preferences import Prefs, demand_factor, market_fit, material_factor
from aerona.engine.polity.law_effects import luxury_factor
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import headcount, stat
from aerona.engine.recording.record import record


@dataclass(frozen=True)
class Quote:
    commodity: CommodityKind
    price: int
    supply: int
    demand: int
    swing: int = 0


@dataclass(frozen=True)
class Swing:
    factor: float = 1.0
    spread: int = 0


@dataclass
class MarketTally:
    districts: int = 0
    priced: int = 0
    noted: int = 0


def market_nodes(book: EconomyBook) -> list[EntityRow]:
    return [community for community in book.communities if book.workshop(community.id, WorkshopKind.MARKET) is not None]


async def currency_of(ctx: TickContext, book: EconomyBook, community_id: int) -> CurrencyRow | None:
    row = book.societies.get(community_id)
    if row is None or row.currency_id is None:
        return None
    return await ctx.session.get(CurrencyRow, row.currency_id)


def inflation(ctx: TickContext, currency: CurrencyRow | None) -> float:
    if currency is None:
        return 1.0
    lost = (PERCENT - currency.purity) / PERCENT + (PERCENT - currency.trust) / (2 * PERCENT)
    return 1 + ctx.rules.money.inflation_pct / PERCENT * lost


def elasticity_of(ctx: TickContext, commodity: CommodityKind) -> float:
    table = ctx.rules.elasticity
    if commodity in STAPLES:
        return table.staple_pct / PERCENT
    return (table.luxury_pct if commodity in LUXURY_GOODS else table.goods_pct) / PERCENT


def income_of(ctx: TickContext, market: EntityRow, commodity: CommodityKind) -> float:
    if commodity not in LUXURY_GOODS:
        return 1.0
    prosperity = stat(market, "prosperity")
    lift = ((prosperity if prosperity is not None else PERCENT // 2) - PERCENT // 2) / PERCENT
    return max(0.0, 1 + lift * ctx.rules.elasticity.income_pct / PERCENT)


def price_of(ctx: TickContext, commodity: CommodityKind, supply: int, demand: int, factor: float, *, markup: float = 1.0, base_price: int | None = None) -> int:
    table = ctx.rules.markets
    base = (base_price if base_price is not None else COMMODITIES[commodity].base_price) * markup
    pressure = (max(1, demand) / max(1, supply)) ** (table.elasticity_pct / PERCENT * elasticity_of(ctx, commodity))
    low = base * table.price_floor_pct / PERCENT
    high = base * table.price_cap_pct / PERCENT
    return round_half_up(min(high, max(low, base * pressure * factor)))


async def material_premium(ctx: TickContext, book: EconomyBook, market: EntityRow, commodity: CommodityKind, tastes: Prefs) -> float:
    lots = [row for row in await lots_of(ctx.session, market.id, commodity) if row.quantity > 0]
    weight = sum(row.quantity for row in lots)
    if weight <= 0:
        return 1.0
    return (
        sum(
            price_premium(ctx.rules, book.materials.props(market.world_id, row.material, row.world_material_id))
            * material_factor(ctx.rules, tastes, row.material)
            * premium(ctx.rules, row.quality)
            * row.quantity
            for row in lots
        )
        / weight
    )


async def noble_demand(ctx: TickContext, book: EconomyBook, market: EntityRow) -> float:
    society = book.societies.get(market.id)
    if society is None:
        return 1.0
    lots = [row for row in await lots_of(ctx.session, market.id, CommodityKind.LUXURIES) if row.quantity > 0]
    if not any(at_least(ctx.rules, row.quality, QualityTier.FINE) for row in lots):
        return 1.0
    return 1 + society.share(SocialClass.NOBLE) / PERCENT * ctx.rules.quality.noble_fine_pct / PERCENT


@memoized(MarketPriceHoldRow)
async def held_markets(session: AsyncSession) -> frozenset[int]:
    return frozenset(await session.scalars(select(MarketPriceHoldRow.market_entity_id).distinct()))


async def price_holds(ctx: TickContext, market_id: int) -> dict[CommodityKind, MarketPriceHoldRow]:
    if market_id not in await held_markets(ctx.session):
        return {}
    return {row.commodity: row for row in await ctx.session.scalars(select(MarketPriceHoldRow).where(MarketPriceHoldRow.market_entity_id == market_id))}


def year_growth(ctx: TickContext, book: EconomyBook, market: EntityRow) -> list[int]:
    years = world_years(ctx.environment, market.world_id or 0, "markets")
    ground = book.ground.region_of(market.id)
    if ground is None:
        return [0 for _ in years]
    season = book.ground.growing_season(ground.world_id)
    return [
        book.ground.weather(ctx.environment.world_seed, ctx.epoch, ground, season, f"market.{market.id}.{year.year}").effect(WeatherEffect.GROWTH)
        for year in years
    ]


def swing_of(ctx: TickContext, market: EntityRow, commodity: CommodityKind, growth: list[int]) -> Swing:
    table = ctx.rules.seasonal
    if not growth:
        return Swing()
    food = COMMODITIES[commodity].aggregate is Commodity.FOOD
    rng = ctx.rng(f"swing.{market.id}.{commodity.value}")
    low, high = table.swing_floor_pct / PERCENT, table.swing_cap_pct / PERCENT
    factors = [
        max(low, min(high, 1 - grown / PERCENT * table.food_swing_pct / PERCENT if food else 1 + rng.uniform(-1.0, 1.0) * table.goods_swing_pct / PERCENT))
        for grown in growth
    ]
    return Swing(sum(factors) / len(factors), round_half_up((max(factors) - min(factors)) * PERCENT))


async def quote_market(ctx: TickContext, book: EconomyBook, market: EntityRow) -> dict[CommodityKind, Quote]:
    factor = inflation(ctx, await currency_of(ctx, book, market.id))
    population = headcount(market)
    quotes: dict[CommodityKind, Quote] = {}
    forbidden = await forbidden_foods(ctx.session, market.id) | await taboos(ctx, market.id)
    diet = diet_demand(ctx.rules, population, await staples_of(ctx.session, market), nourishment_need(ctx.rules, population))
    held = await price_holds(ctx, market.id)
    growth = year_growth(ctx, book, market)
    tastes = await market_fit(ctx.session, market.id)
    plays = await plays_at(ctx.session, ctx.rules, market.id, ctx.epoch)
    goods = await good_book(ctx.session)
    prosperity, piety = stat(market, "prosperity"), stat(market, "piety")
    for commodity in COMMODITIES:
        hold = held.get(commodity)
        supply = await holding(ctx.session, market.id, commodity)
        if hold is not None and hold.supply is not None:
            supply = hold.supply
        demand = round_half_up(diet.get(commodity, epoch_need(ctx.rules, population, commodity)) * ctx.rules.markets.demand_epochs_pct / PERCENT)
        if commodity.value in forbidden:
            demand = round_half_up(demand * ctx.rules.doctrine.dietary_demand_pct / PERCENT)
        if commodity is CommodityKind.LUXURIES:
            demand = round_half_up(demand * await luxury_factor(ctx.session, ctx.rules, market.id, book.societies.get(market.id)))
            demand = round_half_up(demand * await noble_demand(ctx, book, market))
        demand = round_half_up(demand * demand_factor(ctx.rules, tastes, commodity.value) * income_of(ctx, market, commodity))
        demand = round_half_up(demand * goods.demand_scale(ctx.rules, commodity, prosperity=prosperity, piety=piety))
        monopoly = await monopoly_factor(ctx.session, market.id, commodity, ctx.rules.factions.monopoly_price_pct)
        markup = await material_premium(ctx, book, market, commodity, tastes)
        swing = swing_of(ctx, market, commodity, growth)
        price = (
            hold.price
            if hold is not None and hold.price is not None
            else price_of(
                ctx,
                commodity,
                supply,
                demand,
                factor * swing.factor * monopoly * plays.get(commodity, 1.0),
                markup=markup,
                base_price=goods.base_price(commodity),
            )
        )
        quotes[commodity] = Quote(commodity, price, supply, demand, swing.spread)
    ctx.count("taboo_resentment", await resent_taboo(ctx, market.id))
    return quotes


async def epoch_prices(ctx: TickContext) -> dict[int, dict[CommodityKind, MarketPriceRow]]:
    found: dict[int, dict[CommodityKind, MarketPriceRow]] = {}
    for row in await ctx.session.scalars(select(MarketPriceRow).where(MarketPriceRow.epoch == ctx.epoch)):
        found.setdefault(row.market_entity_id, {})[row.commodity] = row
    return found


async def store_quotes(ctx: TickContext, market: EntityRow, quotes: dict[CommodityKind, Quote], current: dict[CommodityKind, MarketPriceRow]) -> None:
    for quote in quotes.values():
        row = current.get(quote.commodity)
        if row is None:
            ctx.session.add(
                MarketPriceRow(
                    market_entity_id=market.id,
                    commodity=quote.commodity,
                    epoch=ctx.epoch,
                    price=quote.price,
                    supply=quote.supply,
                    demand=quote.demand,
                    swing=quote.swing,
                )
            )
        else:
            row.price, row.supply, row.demand, row.swing = quote.price, quote.supply, quote.demand, quote.swing


def aggregate_prices(quotes: dict[CommodityKind, Quote]) -> dict[Commodity, int]:
    prices: dict[Commodity, int] = {}
    for aggregate in Commodity:
        family = [(quote, COMMODITIES[kind].base_price) for kind, quote in quotes.items() if COMMODITIES[kind].aggregate is aggregate]
        weight = sum(base for _, base in family)
        prices[aggregate] = round_half_up(sum(quote.price for quote, _ in family) * PERCENT / weight) if weight else PERCENT
    return prices


async def apply_aggregate_prices(book: EconomyBook, community: EntityRow, quotes: dict[CommodityKind, Quote]) -> None:
    row = book.societies.get(community.id)
    if row is None:
        return
    for aggregate, price in aggregate_prices(quotes).items():
        setattr(row, f"price_{aggregate.value}", max(0, price))


async def raise_district(ctx: TickContext, book: EconomyBook, community: EntityRow, tally: MarketTally) -> None:
    table = ctx.rules.markets
    if book.workshop(community.id, WorkshopKind.MARKET) is not None:
        return
    row = book.societies.get(community.id)
    merchants = row.share(SocialClass.MERCHANT) if row is not None else 0.0
    if merchants < table.district_merchant_pct and not book.knowledge.knows(community.id, KnowledgeBranch.TRADE):
        return
    if not ctx.rng(f"district.{community.id}.{ctx.epoch}").chance(table.district_chance):
        return
    refining = ctx.rules.refining
    ledger = goods_of(ctx.session, ctx.epoch)
    if await holding(ctx.session, community.id, CommodityKind.TIMBER) < refining.build_timber:
        return
    await ledger.take(community.id, CommodityKind.TIMBER, refining.build_timber, GoodsFlow.CONSTRUCTION)
    workshop = WorkshopRow(community_entity_id=community.id, kind=WorkshopKind.MARKET, level=1, built_epoch=ctx.epoch)
    ctx.session.add(workshop)
    book.workshops.setdefault(community.id, {})[WorkshopKind.MARKET] = workshop
    tally.districts += 1
    tally.noted += 1
    await record(ctx, "markets.district", roles={IncidentRole.MAKER: community.id}, facts={"timber": refining.build_timber}, place=community.id)
