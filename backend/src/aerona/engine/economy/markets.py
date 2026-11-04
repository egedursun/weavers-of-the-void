from dataclasses import dataclass, field

from aerona.catalog.commodities import COMMODITIES
from aerona.constants.units import PERCENT
from aerona.db.tables.economy import CurrencyRow, MarketPriceRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, WorkshopKind
from aerona.domain.enums.society import Commodity, KnowledgeBranch, SocialClass
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.stocks import epoch_need, goods_of, holding
from aerona.engine.faith.book import forbidden_foods
from aerona.engine.lore.traditions import resent_taboo, taboos
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import headcount


@dataclass(frozen=True)
class Quote:
    commodity: CommodityKind
    price: int
    supply: int
    demand: int


@dataclass
class MarketTally:
    districts: int = 0
    priced: int = 0
    noted: int = 0
    quotes: dict[int, dict[CommodityKind, Quote]] = field(default_factory=dict)


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


def price_of(ctx: TickContext, commodity: CommodityKind, supply: int, demand: int, factor: float) -> int:
    table = ctx.rules.markets
    base = COMMODITIES[commodity].base_price
    pressure = (max(1, demand) / max(1, supply)) ** (table.elasticity_pct / PERCENT)
    low = base * table.price_floor_pct / PERCENT
    high = base * table.price_cap_pct / PERCENT
    return round_half_up(min(high, max(low, base * pressure * factor)))


async def quote_market(ctx: TickContext, book: EconomyBook, market: EntityRow) -> dict[CommodityKind, Quote]:
    factor = inflation(ctx, await currency_of(ctx, book, market.id))
    population = headcount(market)
    quotes: dict[CommodityKind, Quote] = {}
    forbidden = await forbidden_foods(ctx.session, market.id) | await taboos(ctx, market.id)
    for commodity in COMMODITIES:
        supply = await holding(ctx.session, market.id, commodity)
        demand = round_half_up(epoch_need(ctx.rules, population, commodity) * ctx.rules.markets.demand_epochs_pct / PERCENT)
        if commodity.value in forbidden:
            demand = round_half_up(demand * ctx.rules.doctrine.dietary_demand_pct / PERCENT)
        quotes[commodity] = Quote(commodity, price_of(ctx, commodity, supply, demand, factor), supply, demand)
    ctx.count("taboo_resentment", await resent_taboo(ctx, market.id))
    return quotes


async def store_quotes(ctx: TickContext, market: EntityRow, quotes: dict[CommodityKind, Quote]) -> None:
    for quote in quotes.values():
        row = await ctx.session.get(MarketPriceRow, (market.id, quote.commodity, ctx.epoch))
        if row is None:
            ctx.session.add(
                MarketPriceRow(
                    market_entity_id=market.id, commodity=quote.commodity, epoch=ctx.epoch, price=quote.price, supply=quote.supply, demand=quote.demand
                )
            )
        else:
            row.price, row.supply, row.demand = quote.price, quote.supply, quote.demand


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
    if tally.noted < ctx.rules.market.note_cap:
        tally.noted += 1
        await note(ctx, f"{community.name} laid out a market where merchants gather.", key="markets.district", ids=[community.id], kind=ChronicleKind.TRADE)
