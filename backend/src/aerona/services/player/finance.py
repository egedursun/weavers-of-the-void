from pydantic import Field
from sqlalchemy import select

from aerona.catalog.commodities import COMMODITIES
from aerona.catalog.finance import CREDIT_LABELS, POLICY_LABELS, SPECULATION_LABELS
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.finance import CreditProfileRow, EconomicIndicatorRow, SpeculationRow, TradePolicyRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import SOCIETY_TYPES
from aerona.domain.enums.finance import CreditState, SpeculationStatus, TradePolicyKind
from aerona.engine.economy.stocks import goods_of
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
CREDIT_FIELDS = ("rating", "state", "interest_pct", "reserves", "defaults", "restructured_until")
SPECULATION_FIELDS = ("units", "price", "status", "gain")
INDICATOR_FIELDS = ("output", "price_index", "trade_balance", "treasury", "debt_ratio", "unemployment", "market_access", "black_market")


class SetTradePolicy(Command):
    issuer_id: int
    kind: TradePolicyKind
    commodity: CommodityKind | None = None
    partner_id: int | None = None
    rate_pct: int = Field(default=20, ge=0, le=SPAN)
    reason: str | None = Field(default=None, max_length=120)
    hold: bool = True


class TradePolicyTarget(Command):
    policy_id: int


class SetCredit(Command):
    subject_id: int
    rating: int | None = Field(default=None, ge=0, le=SPAN)
    state: CreditState | None = None
    interest_pct: int | None = Field(default=None, ge=0, le=SPAN)
    reserves: int | None = Field(default=None, ge=0)
    defaults: int | None = Field(default=None, ge=0)
    restructured_until: int | None = Field(default=None, ge=0)
    hold: bool = True


class CreditTarget(Command):
    subject_id: int


class OpenSpeculation(Command):
    merchant_id: int
    market_id: int
    commodity: CommodityKind
    units: int = Field(ge=1)
    price: int = Field(ge=0)


class EditSpeculation(Command):
    speculation_id: int
    units: int | None = Field(default=None, ge=0)
    price: int | None = Field(default=None, ge=0)
    status: SpeculationStatus | None = None
    gain: int | None = None
    hold: bool = True


class SpeculationTarget(Command):
    speculation_id: int


class EditIndicator(Command):
    indicator_id: int
    output: int | None = Field(default=None, ge=0)
    price_index: int | None = Field(default=None, ge=0)
    trade_balance: int | None = None
    treasury: int | None = None
    debt_ratio: int | None = Field(default=None, ge=0)
    unemployment: int | None = Field(default=None, ge=0, le=SPAN)
    market_access: int | None = Field(default=None, ge=0, le=SPAN)
    black_market: int | None = Field(default=None, ge=0)


class IndicatorTarget(Command):
    indicator_id: int


def held(locked: list[str] | None, fields: list[str], hold: bool) -> list[str]:
    found = set(locked or [])
    return sorted(found | set(fields)) if hold else sorted(found - set(fields))


async def node(scope: PlayerScope, node_id: int) -> NodeRow:
    found = await scope.session.get(NodeRow, node_id)
    if found is None:
        raise ValidationFailedError("That record does not exist.")
    return found


async def market(scope: PlayerScope, node_id: int) -> EntityRow:
    found = await scope.session.get(EntityRow, node_id)
    if found is None or found.entity_type not in SOCIETY_TYPES:
        raise ValidationFailedError("Goods are hoarded in a settlement, people or other community.")
    return found


@player_action("trade_policy:set", ActionKind.EDIT_RECORD)
async def set_trade_policy(scope: PlayerScope, command: SetTradePolicy) -> Effect:
    issuer = await node(scope, command.issuer_id)
    if command.partner_id is not None:
        await node(scope, command.partner_id)
    if command.kind is TradePolicyKind.EMBARGO and command.commodity is None and command.partner_id is None:
        raise ValidationFailedError("An embargo needs a partner or a good.")
    row = await scope.session.scalar(
        select(TradePolicyRow).where(
            TradePolicyRow.issuer_node_id == issuer.id,
            TradePolicyRow.kind == command.kind,
            TradePolicyRow.commodity.is_(None) if command.commodity is None else TradePolicyRow.commodity == command.commodity,
            TradePolicyRow.partner_node_id.is_(None) if command.partner_id is None else TradePolicyRow.partner_node_id == command.partner_id,
        )
    )
    if row is None:
        row = TradePolicyRow(
            issuer_node_id=issuer.id,
            kind=command.kind,
            commodity=command.commodity,
            partner_node_id=command.partner_id,
            rate_pct=0,
            since_epoch=await scope.epoch(),
            locked=[],
        )
        scope.session.add(row)
    row.rate_pct = SPAN if command.kind is TradePolicyKind.EMBARGO else command.rate_pct
    row.reason = command.reason or row.reason or "by the Creator's word"
    row.locked = held(row.locked, ["rate_pct", "kind"], command.hold)
    await scope.session.flush()
    good = COMMODITIES[command.commodity].label.lower() if command.commodity is not None else "every good"
    return Effect(f"{issuer.name} lays a {POLICY_LABELS[command.kind].lower()} on {good}.", target_node_id=issuer.id, values={"policy_id": row.id})


@player_action("trade_policy:remove", ActionKind.EDIT_RECORD)
async def remove_trade_policy(scope: PlayerScope, command: TradePolicyTarget) -> Effect:
    row = await scope.session.get(TradePolicyRow, command.policy_id)
    if row is None:
        raise NotFoundError("No such tariff, subsidy or embargo.")
    issuer = row.issuer_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The policy was lifted.", target_node_id=issuer)


@player_action("credit:set", ActionKind.EDIT_RECORD)
async def set_credit(scope: PlayerScope, command: SetCredit) -> Effect:
    subject = await node(scope, command.subject_id)
    row = await scope.session.get(CreditProfileRow, subject.id)
    if row is None:
        row = CreditProfileRow(subject_node_id=subject.id, rating=50, state=CreditState.NORMAL, interest_pct=10, epoch=await scope.epoch(), locked=[])
        scope.session.add(row)
    touched = [name for name in CREDIT_FIELDS if getattr(command, name) is not None]
    if not touched:
        raise ValidationFailedError("Set at least one value.")
    for name in touched:
        setattr(row, name, getattr(command, name))
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"{subject.name} stands {CREDIT_LABELS[row.state].lower()}, rated {row.rating}, borrowing at {row.interest_pct}%.", target_node_id=subject.id)


@player_action("credit:remove", ActionKind.EDIT_RECORD)
async def remove_credit(scope: PlayerScope, command: CreditTarget) -> Effect:
    row = await scope.session.get(CreditProfileRow, command.subject_id)
    if row is None:
        raise NotFoundError("That one has no record of credit.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("Its record of credit was wiped; lenders will judge it anew.", target_node_id=command.subject_id)


@player_action("speculation:open", ActionKind.EDIT_RECORD)
async def open_speculation(scope: PlayerScope, command: OpenSpeculation) -> Effect:
    await node(scope, command.merchant_id)
    place = await market(scope, command.market_id)
    ctx = await scope.context("speculation_open")
    taken = sum(lot.quantity for lot in await goods_of(ctx.session, ctx.epoch).take(place.id, command.commodity, command.units, GoodsFlow.PLAYER))
    row = SpeculationRow(
        merchant_node_id=command.merchant_id,
        market_node_id=place.id,
        commodity=command.commodity,
        units=taken,
        price=command.price,
        status=SpeculationStatus.HOARDING,
        opened_epoch=ctx.epoch,
        gain=0,
        locked=[],
    )
    scope.session.add(row)
    await scope.session.flush()
    return Effect(
        f"A hoard of {taken} {COMMODITIES[command.commodity].label.lower()} was taken off the market of {place.name}.",
        target_node_id=command.merchant_id,
        values={"speculation_id": row.id},
    )


@player_action("speculation:edit", ActionKind.EDIT_RECORD)
async def edit_speculation(scope: PlayerScope, command: EditSpeculation) -> Effect:
    row = await scope.session.get(SpeculationRow, command.speculation_id)
    if row is None:
        raise NotFoundError("No such hoard.")
    touched = [name for name in SPECULATION_FIELDS if getattr(command, name) is not None]
    if not touched:
        raise ValidationFailedError("Set at least one value.")
    for name in touched:
        setattr(row, name, getattr(command, name))
    if row.status is not SpeculationStatus.HOARDING and row.settled_epoch is None:
        row.settled_epoch = await scope.epoch()
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"The hoard is now {SPECULATION_LABELS[row.status].lower()}: {row.units} units bought at {row.price}.", target_node_id=row.merchant_node_id)


@player_action("speculation:remove", ActionKind.EDIT_RECORD)
async def remove_speculation(scope: PlayerScope, command: SpeculationTarget) -> Effect:
    row = await scope.session.get(SpeculationRow, command.speculation_id)
    if row is None:
        raise NotFoundError("No such hoard.")
    if row.status is SpeculationStatus.HOARDING and row.units > 0:
        ctx = await scope.context("speculation_remove")
        await goods_of(ctx.session, ctx.epoch).add(row.market_node_id, row.commodity, row.units, GoodsFlow.PLAYER)
    merchant = row.merchant_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The hoard was struck; whatever it held went back to the market.", target_node_id=merchant)


@player_action("indicator:edit", ActionKind.EDIT_RECORD)
async def edit_indicator(scope: PlayerScope, command: EditIndicator) -> Effect:
    row = await scope.session.get(EconomicIndicatorRow, command.indicator_id)
    if row is None:
        raise NotFoundError("No such record of the economy.")
    touched = [name for name in INDICATOR_FIELDS if getattr(command, name) is not None]
    if not touched:
        raise ValidationFailedError("Set at least one figure.")
    for name in touched:
        setattr(row, name, getattr(command, name))
    row.locked = sorted(set(row.locked or []) | set(touched))
    await scope.session.flush()
    return Effect(f"The record of epoch {row.epoch} was rewritten.", target_node_id=row.subject_node_id)


@player_action("indicator:remove", ActionKind.EDIT_RECORD)
async def remove_indicator(scope: PlayerScope, command: IndicatorTarget) -> Effect:
    row = await scope.session.get(EconomicIndicatorRow, command.indicator_id)
    if row is None:
        raise NotFoundError("No such record of the economy.")
    subject = row.subject_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The record of that epoch was struck.", target_node_id=subject)
