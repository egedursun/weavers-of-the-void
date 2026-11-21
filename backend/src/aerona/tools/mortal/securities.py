from typing import Any

from pydantic import Field

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.core.total import total
from aerona.db.profile_guard import column_frozen
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.finance import CreditProfileRow
from aerona.db.tables.securities import IssuedSecurityRow, SecurityHoldingRow, StockExchangeRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.securities import DEBT_KINDS, SecurityKind, TradeSide
from aerona.engine.economy.purse import coin_of, give_coin, take_coin
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.transfers import move_amount
from aerona.engine.securities.exchanges import list_on
from aerona.engine.securities.holdings import holding, holdings_of
from aerona.engine.securities.pricing import price_row
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.monetary import controls

AMOUNT_MAX = 100000
FACE = 10
DEBT_COUPON = 5
IMPACT_DIVISOR = 2
SIDE_SIGN = total(TradeSide, {TradeSide.BUY: 1, TradeSide.SELL: -1})


class ListSecurityInput(ToolInput):
    issuer_id: int
    kind: SecurityKind
    amount: int = Field(ge=1, le=AMOUNT_MAX)
    exchange_id: int


class TradeSecurityInput(ToolInput):
    security_id: int
    amount: int = Field(ge=1, le=AMOUNT_MAX)
    side: TradeSide


async def list_security_tool(call: MortalCall, args: ListSecurityInput) -> str:
    issuer = await living_entity(call.session, args.issuer_id)
    exchange = await call.session.get(StockExchangeRow, args.exchange_id)
    if issuer is None or exchange is None:
        fail(MortalResult.SECURITIES_REFUSED, why="the issuer and the exchange must both exist")
    if not await controls(call, issuer.id):
        fail(MortalResult.SECURITIES_REFUSED, why="only those who rule or head an issuer list its claims")
    if held(issuer.id) or (exchange.settlement_entity_id is not None and held(exchange.settlement_entity_id)):
        fail(MortalResult.SECURITIES_REFUSED, why="a god holds it as it is")
    if exchange.listing_fee and not await take_coin(call.session, call.tick.rules, issuer, exchange.listing_fee):
        fail(MortalResult.SECURITIES_REFUSED, why=f"the issuer cannot pay the listing fee of {exchange.listing_fee}")
    owner = await living_entity(call.session, exchange.owner_node_id)
    if owner is not None and exchange.listing_fee:
        await give_coin(call.session, call.tick.rules, owner, exchange.listing_fee)
    credit = await call.session.get(CreditProfileRow, issuer.id)
    debt = args.kind in DEBT_KINDS
    security = IssuedSecurityRow(
        name=f"the {spoken(args.kind)} of {issuer.name}",
        issuer_node_id=issuer.id,
        kind=args.kind,
        amount=args.amount,
        face_value=FACE,
        coupon_pct=min(PERCENT, credit.interest_pct if credit is not None else DEBT_COUPON) if debt else 0,
        maturity_epoch=call.tick.epoch + call.tick.rules.securities.bond_term_epochs if debt else None,
        price=FACE,
        listed_epoch=call.tick.epoch,
        locked=[],
    )
    call.session.add(security)
    await call.session.flush()
    call.session.add(SecurityHoldingRow(holder_node_id=issuer.id, security_id=security.id, amount=args.amount, bought_price=FACE, locked=[]))
    await list_on(call.tick, security, exchange)
    call.target(issuer.id)
    return result(MortalResult.SECURITY_LISTED, security=security.name, amount=args.amount, exchange=exchange.name)


async def tradable(call: MortalCall, security_id: int) -> tuple[IssuedSecurityRow, StockExchangeRow]:
    security = await call.session.get(IssuedSecurityRow, security_id)
    exchange = await call.session.get(StockExchangeRow, security.exchange_id) if security is not None and security.exchange_id is not None else None
    if security is None or exchange is None or security.delisted_epoch is not None:
        fail(MortalResult.SECURITIES_REFUSED, why="only a claim listed on an exchange is traded")
    if held(security.issuer_node_id):
        fail(MortalResult.SECURITIES_REFUSED, why="a god holds its issuer as it is")
    return security, exchange


def nudge(security: IssuedSecurityRow, amount: int, side: TradeSide) -> None:
    if "price" in (security.locked or []):
        return
    impact = round_half_up(security.price * amount / max(1, security.amount) / IMPACT_DIVISOR)
    security.price = max(1, security.price + impact * SIDE_SIGN[side])


async def buy(call: MortalCall, security: IssuedSecurityRow, exchange: StockExchangeRow, amount: int) -> int:
    sellers = [row for row in await holdings_of(call.session, security.id) if row.holder_node_id != call.me.id and not held(row.holder_node_id)]
    if not sellers or sellers[0].amount < amount:
        fail(MortalResult.SECURITIES_REFUSED, why="no one holds that many to sell")
    seller = sellers[0]
    mine = await holding(call.session, security.id, call.me.id)
    if column_frozen(seller, "amount") or (mine is not None and column_frozen(mine, "amount")):
        fail(MortalResult.SECURITIES_REFUSED, why="a god holds that holding as it is")
    cost = security.price * amount
    borrowed = max(0, cost - await coin_of(call.session, call.tick.rules, call.me))
    if borrowed * PERCENT > cost * exchange.margin_pct:
        fail(MortalResult.SECURITIES_REFUSED, why=f"that costs {cost}, more than your purse and what the exchange lends")
    if not await take_coin(call.session, call.tick.rules, call.me, cost - borrowed):
        fail(MortalResult.SECURITIES_REFUSED, why=f"you cannot pay {cost - borrowed}")
    payee = await living_entity(call.session, seller.holder_node_id)
    if payee is not None:
        await give_coin(call.session, call.tick.rules, payee, cost)
    if mine is None:
        mine = SecurityHoldingRow(holder_node_id=call.me.id, security_id=security.id, amount=0, bought_price=security.price, locked=[])
        call.session.add(mine)
    move_amount(seller, mine, "amount", amount)
    mine.on_margin += borrowed
    mine.bought_price = security.price
    return cost


async def sell(call: MortalCall, security: IssuedSecurityRow, amount: int) -> int:
    mine = await holding(call.session, security.id, call.me.id)
    if mine is None or mine.amount < amount:
        fail(MortalResult.SECURITIES_REFUSED, why="you do not hold that many")
    if column_frozen(mine, "amount"):
        fail(MortalResult.SECURITIES_REFUSED, why="a god holds that holding as it is")
    issuer = await living_entity(call.session, security.issuer_node_id)
    proceeds = security.price * amount
    if issuer is None or issuer.id == call.me.id or not await take_coin(call.session, call.tick.rules, issuer, proceeds):
        fail(MortalResult.SECURITIES_REFUSED, why="no one will buy them back at that price")
    repaid = min(mine.on_margin, round_half_up(mine.on_margin * amount / mine.amount))
    mine.on_margin -= repaid
    await give_coin(call.session, call.tick.rules, call.me, proceeds - repaid)
    back = await holding(call.session, security.id, issuer.id)
    if back is None:
        back = SecurityHoldingRow(holder_node_id=issuer.id, security_id=security.id, amount=0, bought_price=security.price, locked=[])
        call.session.add(back)
    move_amount(mine, back, "amount", amount)
    return proceeds


async def trade_security_tool(call: MortalCall, args: TradeSecurityInput) -> str:
    security, exchange = await tradable(call, args.security_id)
    price = security.price
    paid = await sell(call, security, args.amount) if args.side is TradeSide.SELL else await buy(call, security, exchange, args.amount)
    nudge(security, args.amount, args.side)
    row = await price_row(call.tick, security)
    row.volume += args.amount
    issuer: EntityRow | None = await call.session.get(EntityRow, security.issuer_node_id)
    call.target(issuer.id if issuer is not None else None)
    side = "bought" if args.side is TradeSide.BUY else "sold"
    await call.record(
        "securities.traded",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: security.issuer_node_id},
        facts={"security": security.name, "side": side, "amount": args.amount, "price": price},
    )
    return result(MortalResult.SECURITY_TRADED, side=side, amount=args.amount, security=security.name, total=paid, price=security.price)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    trade = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.LIST_SECURITY, AgentKind.MORTAL, ListSecurityInput, trade, list_security_tool),
        ToolSpec(MortalToolId.TRADE_SECURITY, AgentKind.MORTAL, TradeSecurityInput, trade, trade_security_tool),
    ]
