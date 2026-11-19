from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PER_MILLE, PERCENT
from aerona.db.record_context import Term
from aerona.db.tables.economy import CurrencyRow, GoodsFlowRow, LoanRow, TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.orders import BillOfExchangeRow, ExchangeRateRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import GoodsFlow, LoanStatus, TradeRouteStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin, take_coin
from aerona.engine.eras.effects import era_techniques
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record


@dataclass
class ExchangeTally:
    rates: int = 0
    shocks: int = 0
    changed: int = 0
    drawn: int = 0
    settled: int = 0


async def coin_of_town(ctx: TickContext, town_id: int) -> CurrencyRow | None:
    society = await ctx.session.get(CommunitySocietyRow, town_id)
    return await ctx.session.get(CurrencyRow, society.currency_id) if society is not None and society.currency_id is not None else None


async def balance_of(ctx: TickContext, currency: CurrencyRow) -> int:
    users = select(CommunitySocietyRow.entity_id).where(CommunitySocietyRow.currency_id == currency.id)
    flowed = await ctx.session.scalar(
        select(func.sum(GoodsFlowRow.quantity)).where(
            GoodsFlowRow.epoch == ctx.epoch - 1, GoodsFlowRow.flow == GoodsFlow.TRADE, GoodsFlowRow.community_entity_id.in_(users)
        )
    )
    return -int(flowed or 0)


async def worth_of(ctx: TickContext, currency: CurrencyRow) -> int:
    table = ctx.rules.exchange_rates
    balance = clamp_int(await balance_of(ctx, currency) * table.balance_pct // PERCENT, -PERCENT // 2, PERCENT // 2)
    glut = PERCENT * PERCENT // (PERCENT + currency.supply * table.supply_pct // PERCENT)
    return max(1, currency.purity * (PERCENT // 2 + currency.trust // 2) // PERCENT * (PERCENT + balance) // PERCENT * glut // PERCENT)


async def changer_at(ctx: TickContext, market: EntityRow) -> EntityRow | None:
    found = await ctx.session.scalar(
        select(EntityRow)
        .join(SkillRow, SkillRow.holder_node_id == EntityRow.id)
        .where(
            await present_in(ctx.session, market),
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            SkillRow.skill == SkillKind.ACCOUNTING,
            SkillRow.level >= ctx.rules.exchange_rates.changer_skill,
        )
        .order_by(SkillRow.level.desc(), EntityRow.id)
        .limit(1)
    )
    return found


async def rate_for(ctx: TickContext, base: CurrencyRow, quote: CurrencyRow, market_id: int) -> ExchangeRateRow:
    row = await ctx.session.scalar(
        select(ExchangeRateRow).where(
            ExchangeRateRow.base_currency_id == base.id, ExchangeRateRow.quote_currency_id == quote.id, ExchangeRateRow.market_entity_id == market_id
        )
    )
    if row is None:
        row = ExchangeRateRow(base_currency_id=base.id, quote_currency_id=quote.id, market_entity_id=market_id, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    return row


async def shock_debtors(ctx: TickContext, base: CurrencyRow, quote: CurrencyRow, rise: int) -> int:
    users = select(CommunitySocietyRow.entity_id).where(CommunitySocietyRow.currency_id == quote.id)
    hit = 0
    for loan in list(
        await ctx.session.scalars(
            select(LoanRow).where(LoanRow.currency_id == base.id, LoanRow.status == LoanStatus.OPEN, LoanRow.borrower_entity_id.in_(users)).order_by(LoanRow.id)
        )
    ):
        if held(loan.borrower_entity_id):
            continue
        loan.principal += round_half_up(loan.principal * min(rise, ctx.rules.exchange_rates.shock_cap) / PERCENT)
        hit += 1
    return hit


async def settle_rate(ctx: TickContext, route: TradeRouteProfileRow, tally: ExchangeTally) -> None:
    table = ctx.rules.exchange_rates
    base, quote = await coin_of_town(ctx, route.first_market_id), await coin_of_town(ctx, route.second_market_id)
    market = await ctx.session.get(EntityRow, route.first_market_id)
    if base is None or quote is None or base.id == quote.id or market is None or held(market.id):
        return
    row = await rate_for(ctx, base, quote, market.id)
    before = row.rate
    if "rate" not in row.locked:
        row.rate = max(1, await worth_of(ctx, base) * PERCENT // await worth_of(ctx, quote))
    if "spread_pct" not in row.locked:
        weak = min(base.trust, quote.trust)
        row.spread_pct = clamp_int(table.base_spread + (PERCENT - weak) * table.trust_spread // (PERCENT // 2), 0, PERCENT)
    changer = await changer_at(ctx, market) if "changer_node_id" not in row.locked else await ctx.session.get(EntityRow, row.changer_node_id or 0)
    row.changer_node_id = changer.id if changer is not None else None
    if changer is not None and row.volume and not held(changer.id):
        await give_coin(ctx.session, ctx.rules, changer, round_half_up(row.volume * row.spread_pct * table.changer_share / PERCENT / PERCENT))
        tally.changed += 1
    if before and row.rate * PERCENT >= before * (PERCENT + table.shock_pct):
        hit = await shock_debtors(ctx, base, quote, (row.rate - before) * PERCENT // before)
        tally.shocks += 1
        await record(
            ctx,
            "exchange.shock",
            roles={IncidentRole.PLACE: market.id},
            facts={"base": base.name, "quote": quote.name, "rise": (row.rate - before) * PERCENT // before, "debts_hit": hit},
            terms=(Term("exchange.rate_before", before), Term("exchange.rate_after", row.rate), Term("exchange.shock_pct", table.shock_pct)),
            place=market.id,
        )
    row.volume, row.updated_epoch = 0, ctx.epoch
    tally.rates += 1


async def spread_between(ctx: TickContext, seller_id: int, buyer_id: int) -> tuple[int, ExchangeRateRow | None]:
    seller, buyer = await coin_of_town(ctx, seller_id), await coin_of_town(ctx, buyer_id)
    if seller is None or buyer is None or seller.id == buyer.id:
        return 0, None
    row = await ctx.session.scalar(
        select(ExchangeRateRow)
        .where(
            ((ExchangeRateRow.base_currency_id == seller.id) & (ExchangeRateRow.quote_currency_id == buyer.id))
            | ((ExchangeRateRow.base_currency_id == buyer.id) & (ExchangeRateRow.quote_currency_id == seller.id))
        )
        .order_by(ExchangeRateRow.id)
        .limit(1)
    )
    if row is None or not row.convertible:
        return ctx.rules.exchange_rates.unconvertible_pct, row
    return row.spread_pct, row


async def exchange_cost(ctx: TickContext, seller_id: int, buyer_id: int, cost: int) -> int:
    spread, row = await spread_between(ctx, seller_id, buyer_id)
    if row is not None and "volume" not in row.locked:
        row.volume += cost
    return round_half_up(cost * spread / PERCENT)


async def banking_between(ctx: TickContext, first_id: int, second_id: int) -> bool:
    for end in (first_id, second_id):
        if Technique.BANKING not in await era_techniques(ctx.session, end):
            return False
    return True


async def draw_bills(ctx: TickContext, tally: ExchangeTally) -> None:
    table = ctx.rules.exchange_rates
    routes = await ctx.session.scalars(
        select(TradeRouteProfileRow).where(TradeRouteProfileRow.status == TradeRouteStatus.OPEN, TradeRouteProfileRow.last_traffic_epoch == ctx.epoch - 1)
    )
    for route in list(routes):
        first, second = route.first_market_id, route.second_market_id
        if held(first) or held(second) or not await banking_between(ctx, first, second):
            continue
        drawn = await ctx.session.scalar(
            select(func.count())
            .select_from(BillOfExchangeRow)
            .where(BillOfExchangeRow.from_entity_id == first, BillOfExchangeRow.to_entity_id == second, BillOfExchangeRow.settled.is_(False))
        )
        if int(drawn or 0) >= table.bills_per_route:
            continue
        markets = [await ctx.session.get(EntityRow, first), await ctx.session.get(EntityRow, second)]
        smaller = min(stat_or(market, "population", 0) if market is not None else 0 for market in markets)
        ctx.session.add(
            BillOfExchangeRow(
                drawer_node_id=second,
                payee_node_id=first,
                from_entity_id=first,
                to_entity_id=second,
                amount=max(table.bill_amount, round_half_up(table.bill_amount * smaller / PER_MILLE)),
                issued_epoch=ctx.epoch,
                locked=[],
            )
        )
        tally.drawn += 1
    await ctx.session.flush()


async def settle_bills(ctx: TickContext, tally: ExchangeTally) -> None:
    for bill in list(
        await ctx.session.scalars(select(BillOfExchangeRow).where(BillOfExchangeRow.settled.is_(False), BillOfExchangeRow.issued_epoch < ctx.epoch))
    ):
        if "settled" in bill.locked or held(bill.drawer_node_id, bill.payee_node_id):
            continue
        drawer, payee = await ctx.session.get(EntityRow, bill.drawer_node_id), await ctx.session.get(EntityRow, bill.payee_node_id)
        if drawer is None or payee is None:
            continue
        if await take_coin(ctx.session, ctx.rules, drawer, bill.amount):
            await give_coin(ctx.session, ctx.rules, payee, bill.amount)
            bill.settled = True
            tally.settled += 1


async def billed_between(ctx: TickContext, ends: tuple[int, int]) -> float:
    found = await ctx.session.scalar(
        select(BillOfExchangeRow.id)
        .where(BillOfExchangeRow.settled.is_(False), BillOfExchangeRow.from_entity_id.in_(ends), BillOfExchangeRow.to_entity_id.in_(ends))
        .limit(1)
    )
    return 1 - ctx.rules.exchange_rates.bill_loss_pct / PERCENT if found is not None else 1.0


async def keep_exchange(ctx: TickContext, tally: ExchangeTally) -> None:
    for route in list(
        await ctx.session.scalars(
            select(TradeRouteProfileRow).where(TradeRouteProfileRow.status == TradeRouteStatus.OPEN).order_by(TradeRouteProfileRow.route_entity_id)
        )
    ):
        await settle_rate(ctx, route, tally)
    await settle_bills(ctx, tally)
    await draw_bills(ctx, tally)
    await ctx.session.flush()
