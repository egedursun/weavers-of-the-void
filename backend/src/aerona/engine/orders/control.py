from collections.abc import Mapping
from dataclasses import dataclass, field

from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import HouseholdRow
from aerona.db.tables.orders import (
    BILL_FIELDS,
    CHAIN_FIELDS,
    HOARD_FIELDS,
    ORDER_FIELDS,
    ORDER_KIND_FIELDS,
    PUTTING_OUT_FIELDS,
    RATE_FIELDS,
    SAVING_FIELDS,
    TOURISM_FIELDS,
    TRANSITION_FIELDS,
    BillOfExchangeRow,
    ChainHoldingRow,
    EconomicOrderKindRow,
    EconomicOrderRow,
    ExchangeRateRow,
    HoardRow,
    OrderTransitionRow,
    PuttingOutRow,
    SavingRow,
    TouristFlowRow,
)
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.orders import TransitionStage
from aerona.engine.collective.control import saved
from aerona.engine.context import TickContext
from aerona.engine.cycles.control import node_exists
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import Values, allowed, found
from aerona.engine.orders.economy import OrderTally, advance, keep_economy
from aerona.engine.orders.exchange import ExchangeTally, keep_exchange
from aerona.engine.orders.putting_out import PuttingOutTally, keep_putting_out
from aerona.engine.orders.savings import SavingTally, keep_savings
from aerona.engine.orders.tourism import TourismTally, keep_tourism


@dataclass(frozen=True)
class Kind:
    table: type[Base]
    fields: tuple[str, ...]
    label: str
    keys: tuple[str, ...]


KINDS: Mapping[str, Kind] = {
    "saving": Kind(SavingRow, SAVING_FIELDS, "saving of a household", ("household_id",)),
    "hoard": Kind(HoardRow, HOARD_FIELDS, "hoard", ("id",)),
    "exchange_rate": Kind(ExchangeRateRow, RATE_FIELDS, "exchange rate", ("id",)),
    "bill_of_exchange": Kind(BillOfExchangeRow, BILL_FIELDS, "bill of exchange", ("id",)),
    "economic_order": Kind(EconomicOrderRow, ORDER_FIELDS, "economic order", ("id",)),
    "economic_order_kind": Kind(EconomicOrderKindRow, ORDER_KIND_FIELDS, "named economic order", ("id",)),
    "order_transition": Kind(OrderTransitionRow, TRANSITION_FIELDS, "change of economic order", ("id",)),
    "putting_out": Kind(PuttingOutRow, PUTTING_OUT_FIELDS, "work put out", ("id",)),
    "chain_holding": Kind(ChainHoldingRow, CHAIN_FIELDS, "share in a chain", ("holder_entity_id", "town_entity_id", "product")),
    "tourist_flow": Kind(TouristFlowRow, TOURISM_FIELDS, "flow of travellers", ("id",)),
}
STAMPS = {
    "saving": "updated_epoch",
    "hoard": "hidden_epoch",
    "exchange_rate": "updated_epoch",
    "bill_of_exchange": "issued_epoch",
    "economic_order": "since_epoch",
    "order_transition": "started_epoch",
    "putting_out": "since_epoch",
    "chain_holding": "since_epoch",
    "tourist_flow": "epoch",
}
POLITY_KEYS = ("polity_entity_id",)


async def checked(ctx: TickContext, values: Values) -> None:
    for name, value in values.items():
        if isinstance(value, int) and name.endswith(("_node_id", "_entity_id")):
            await node_exists(ctx, value, name.removesuffix("_id").replace("_", " "))
    for name in POLITY_KEYS:
        value = values.get(name)
        entity = await ctx.session.get(EntityRow, value) if isinstance(value, int) else None
        if isinstance(value, int) and (entity is None or entity.entity_type is not EntityType.POLITY):
            raise ValidationFailedError("An economic order is held by a realm.")
    household = values.get("household_id")
    if isinstance(household, int) and await ctx.session.get(HouseholdRow, household) is None:
        raise ValidationFailedError("No such household.")
    for name in ("base_currency_id", "quote_currency_id"):
        value = values.get(name)
        if isinstance(value, int) and await ctx.session.get(CurrencyRow, value) is None:
            raise ValidationFailedError("A rate is set between two coins that exist.")
    if values.get("base_currency_id") is not None and values.get("base_currency_id") == values.get("quote_currency_id"):
        raise ValidationFailedError("A coin has no rate against itself.")


def key_of(kind: Kind, keys: Values) -> object:
    picked = tuple(keys[name] for name in kind.keys)
    return picked[0] if len(picked) == 1 else picked


async def set_record(ctx: TickContext, name: str, keys: Values, values: Values) -> Base:
    kind = KINDS[name]
    await checked(ctx, {**keys, **values})
    row = await ctx.session.get(kind.table, key_of(kind, keys)) if "id" not in kind.keys else None
    if row is None:
        stamp = {STAMPS[name]: ctx.epoch} if name in STAMPS else {}
        row = await saved(ctx, kind.table(**keys, **values, **stamp, locked=[]))
    else:
        apply(row, allowed(values, kind.fields, kind.label), [])
        await ctx.session.flush()
    return row


async def edit_record(ctx: TickContext, name: str, key: object, values: Values, release: list[str]) -> Base:
    kind = KINDS[name]
    await checked(ctx, values)
    row = apply(await found(ctx, kind.table, key, kind.label), allowed(values, kind.fields, kind.label), release)
    await ctx.session.flush()
    return row


async def delete_record(ctx: TickContext, name: str, key: object) -> None:
    kind = KINDS[name]
    await ctx.session.delete(await found(ctx, kind.table, key, kind.label))
    await ctx.session.flush()


async def delete_saving(ctx: TickContext, household_id: int) -> None:
    row = await ctx.session.get(SavingRow, household_id)
    if row is None:
        raise ValidationFailedError("No such saving of a household.")
    await ctx.session.delete(row)
    await ctx.session.flush()


async def advance_transition(ctx: TickContext, transition_id: int) -> OrderTransitionRow:
    row = await found(ctx, OrderTransitionRow, transition_id, "change of economic order")
    if row.stage not in (TransitionStage.PROCLAIMED, TransitionStage.TRANSFERRING):
        raise ValidationFailedError("This change of economic order has ended.")
    row.started_epoch = ctx.epoch
    await advance(ctx, row, OrderTally())
    await ctx.session.flush()
    return row


@dataclass
class OrdersRun:
    savings: SavingTally = field(default_factory=SavingTally)
    exchange: ExchangeTally = field(default_factory=ExchangeTally)
    economy: OrderTally = field(default_factory=OrderTally)
    putting_out: PuttingOutTally = field(default_factory=PuttingOutTally)
    tourism: TourismTally = field(default_factory=TourismTally)


async def run_orders(ctx: TickContext) -> OrdersRun:
    tally = OrdersRun()
    await keep_savings(ctx, tally.savings)
    await keep_exchange(ctx, tally.exchange)
    await keep_economy(ctx, tally.economy)
    await keep_putting_out(ctx, tally.putting_out)
    await keep_tourism(ctx, tally.tourism)
    return tally
