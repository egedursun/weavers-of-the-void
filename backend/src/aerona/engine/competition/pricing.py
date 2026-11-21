from sqlalchemy import select

from aerona.catalog.competition import BUYER_POWER_WEIGHT, CARTEL_PRICE_WEIGHT
from aerona.constants.units import PERCENT
from aerona.db.tables.competition import CartelRow, MarketStructureRow, PriceWarRow
from aerona.domain.enums.competition import CompetitionClause, EntryBarrier, PriceWarOutcome
from aerona.domain.enums.economy import CommodityKind
from aerona.engine.competition.clauses import clause_strength
from aerona.engine.context import TickContext


def base_factor(ctx: TickContext, row: MarketStructureRow) -> float:
    table = ctx.rules.competition
    factor = 1 + row.concentration / PERCENT * table.price_per_concentration_pct / PERCENT
    barriers = sum(int(value) for value in (row.barriers or {}).values()) / len(EntryBarrier)
    factor *= 1 + barriers / PERCENT * table.barrier_price_pct / PERCENT
    return factor * (1 - BUYER_POWER_WEIGHT[row.form] / PERCENT * table.buyer_power_pct / PERCENT)


async def market_factors(ctx: TickContext, market_id: int) -> dict[CommodityKind, float]:
    table = ctx.rules.competition
    rows = list(await ctx.session.scalars(select(MarketStructureRow).where(MarketStructureRow.market_entity_id == market_id).order_by(MarketStructureRow.id)))
    if not rows:
        return {}
    cartels = [
        cartel
        for cartel in await ctx.session.scalars(select(CartelRow).where(CartelRow.broken_epoch.is_(None)).order_by(CartelRow.id))
        if market_id in (cartel.markets or [])
    ]
    wars = {
        war.commodity: war
        for war in await ctx.session.scalars(
            select(PriceWarRow).where(PriceWarRow.market_entity_id == market_id, PriceWarRow.outcome == PriceWarOutcome.ONGOING).order_by(PriceWarRow.id)
        )
    }
    cap = await clause_strength(ctx, market_id, CompetitionClause.PRICE_CAP)
    found: dict[CommodityKind, float] = {}
    for row in rows:
        factor = base_factor(ctx, row)
        cartel = next((item for item in cartels if item.commodity is row.commodity), None)
        if cartel is not None:
            factor *= 1 + cartel.discipline / PERCENT * table.cartel_price_pct / PERCENT * CARTEL_PRICE_WEIGHT[cartel.aim] / PERCENT
        war = wars.get(row.commodity)
        if war is not None:
            factor *= max(table.price_war_floor_pct / PERCENT, 1 - war.cut_pct / PERCENT)
        if cap:
            factor = min(factor, 1 + (PERCENT - cap) / PERCENT)
        found[row.commodity] = factor
    return found
