from collections.abc import Mapping

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.commodities import COMMODITIES
from aerona.constants.units import PERCENT
from aerona.db.tables.economy import MarketPriceRow
from aerona.domain.enums.economy import CommodityKind
from aerona.engine.economy.stocks import epoch_need, holdings
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules


def scarcity_index(rules: Rules, supply: int, demand: int) -> int:
    table = rules.markets
    pressure = (max(1, demand) / max(1, supply)) ** (table.elasticity_pct / PERCENT)
    return clamp_int(round_half_up(pressure * PERCENT), table.price_floor_pct, table.price_cap_pct)


async def market_index(session: AsyncSession, community_id: int) -> dict[CommodityKind, int]:
    latest = await session.scalar(select(func.max(MarketPriceRow.epoch)).where(MarketPriceRow.market_entity_id == community_id))
    if latest is None:
        return {}
    rows = await session.execute(
        select(MarketPriceRow.commodity, MarketPriceRow.price).where(MarketPriceRow.market_entity_id == community_id, MarketPriceRow.epoch == latest)
    )
    return {commodity: round_half_up(price * PERCENT / max(1, COMMODITIES[commodity].base_price)) for commodity, price in rows}


async def local_prices(session: AsyncSession, rules: Rules, community_id: int, population: int) -> dict[CommodityKind, int]:
    quoted = await market_index(session, community_id)
    held = await holdings(session, community_id)
    demand = {kind: round_half_up(epoch_need(rules, population, kind) * rules.markets.demand_epochs_pct / PERCENT) for kind in COMMODITIES}
    return {kind: quoted.get(kind, scarcity_index(rules, held.get(kind, 0), demand[kind])) for kind in COMMODITIES}


def dearest(prices: Mapping[CommodityKind, int], kinds: tuple[CommodityKind, ...]) -> CommodityKind | None:
    return max(kinds, key=lambda kind: (prices.get(kind, PERCENT), kind.value), default=None)


def cheapest(prices: Mapping[CommodityKind, int], kinds: tuple[CommodityKind, ...]) -> CommodityKind | None:
    return min(kinds, key=lambda kind: (prices.get(kind, PERCENT), kind.value), default=None)
