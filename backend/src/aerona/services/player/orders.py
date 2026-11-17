from aerona.core.grammar import several, spoken
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.orders import (
    AllocationMode,
    Compensation,
    DistributionRule,
    HoardState,
    OrderLabour,
    OwnershipRegime,
    SavingForm,
    TouristSight,
    TransitionKind,
)
from aerona.engine.orders import control
from aerona.engine.orders.economy import begin_transition
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class RunNow(Command):
    pass


class SavingDraft(Command):
    household_id: int
    share_pct: int = 10
    form: SavingForm = SavingForm.HOARD
    saved: int = 0


class SavingTarget(Command):
    household_id: int


class SavingEdit(Edited):
    household_id: int


class HoardDraft(Command):
    place_id: int
    holder_id: int | None = None
    amount: int = 10
    state: HoardState = HoardState.HIDDEN


class HoardTarget(Command):
    record_id: int


class HoardEdit(Edited):
    record_id: int


class ExchangeRateDraft(Command):
    base_currency_id: int
    quote_currency_id: int
    market_id: int | None = None
    rate: int = 100
    spread_pct: int = 4
    convertible: bool = True


class ExchangeRateTarget(Command):
    record_id: int


class ExchangeRateEdit(Edited):
    record_id: int


class BillOfExchangeDraft(Command):
    drawer_id: int
    payee_id: int
    from_id: int
    to_id: int
    amount: int = 20


class BillOfExchangeTarget(Command):
    record_id: int


class BillOfExchangeEdit(Edited):
    record_id: int


class EconomicOrderDraft(Command):
    polity_id: int
    sector: CommodityKind | None = None
    ownership: OwnershipRegime = OwnershipRegime.HOUSEHOLD
    allocation: AllocationMode = AllocationMode.MARKET
    labour: OrderLabour = OrderLabour.FREE
    distribution: DistributionRule = DistributionRule.BY_HOLDING
    planning_capacity: int = 30


class EconomicOrderTarget(Command):
    record_id: int


class EconomicOrderEdit(Edited):
    record_id: int


class EconomicOrderKindDraft(Command):
    name: str
    ownership: OwnershipRegime = OwnershipRegime.HOUSEHOLD
    allocation: AllocationMode = AllocationMode.MARKET
    labour: OrderLabour = OrderLabour.FREE
    distribution: DistributionRule = DistributionRule.BY_HOLDING


class EconomicOrderKindTarget(Command):
    record_id: int


class EconomicOrderKindEdit(Edited):
    record_id: int


class OrderTransitionDraft(Command):
    polity_id: int
    sector: CommodityKind | None = None
    kind: TransitionKind = TransitionKind.LAND_REFORM
    compensation: Compensation = Compensation.NONE


class OrderTransitionTarget(Command):
    record_id: int


class OrderTransitionEdit(Edited):
    record_id: int


class PuttingOutDraft(Command):
    merchant_id: int
    town_id: int
    raw: CommodityKind = CommodityKind.WOOL
    product: CommodityKind = CommodityKind.CLOTH
    volume: int = 10


class PuttingOutTarget(Command):
    record_id: int


class PuttingOutEdit(Edited):
    record_id: int


class ChainHoldingDraft(Command):
    holder_id: int
    town_id: int
    product: CommodityKind
    share_pct: int = 20


class ChainHoldingTarget(Command):
    holder_id: int
    town_id: int
    product: CommodityKind


class ChainHoldingEdit(Edited):
    holder_id: int
    town_id: int
    product: CommodityKind


class TouristFlowDraft(Command):
    origin_id: int
    sight_id: int
    sight: TouristSight = TouristSight.WONDER
    visitors: int = 20
    income: int = 40


class TouristFlowTarget(Command):
    record_id: int


class TouristFlowEdit(Edited):
    record_id: int


@player_action("saving:set", ActionKind.EDIT_RECORD)
async def saving_set(scope: PlayerScope, command: SavingDraft) -> Effect:
    row = await control.set_record(
        await scope.context("saving_set"),
        "saving",
        {"household_id": command.household_id},
        {"share_pct": command.share_pct, "form": command.form, "saved": command.saved},
    )
    return Effect("The household saves so.", values={"record_id": getattr(row, "id", 0)})


@player_action("saving:edit", ActionKind.EDIT_RECORD)
async def saving_edit(scope: PlayerScope, command: SavingEdit) -> Effect:
    await control.edit_record(await scope.context("saving_edit"), "saving", command.household_id, command.values, command.release)
    return Effect("The saving is set so.")


@player_action("saving:delete", ActionKind.EDIT_RECORD)
async def saving_delete(scope: PlayerScope, command: SavingTarget) -> Effect:
    await control.delete_saving(await scope.context("saving_delete"), command.household_id)
    return Effect("The household saves nothing.")


@player_action("hoard:create", ActionKind.EDIT_RECORD)
async def hoard_create(scope: PlayerScope, command: HoardDraft) -> Effect:
    row = await control.set_record(
        await scope.context("hoard_create"),
        "hoard",
        {},
        {"place_entity_id": command.place_id, "holder_node_id": command.holder_id, "amount": command.amount, "state": command.state},
    )
    return Effect("The hoard is put away.", values={"record_id": getattr(row, "id", 0)})


@player_action("hoard:edit", ActionKind.EDIT_RECORD)
async def hoard_edit(scope: PlayerScope, command: HoardEdit) -> Effect:
    await control.edit_record(await scope.context("hoard_edit"), "hoard", command.record_id, command.values, command.release)
    return Effect("The hoard is set so.")


@player_action("hoard:delete", ActionKind.EDIT_RECORD)
async def hoard_delete(scope: PlayerScope, command: HoardTarget) -> Effect:
    await control.delete_record(await scope.context("hoard_delete"), "hoard", command.record_id)
    return Effect("The hoard is gone.")


@player_action("exchange_rate:create", ActionKind.EDIT_RECORD)
async def exchange_rate_create(scope: PlayerScope, command: ExchangeRateDraft) -> Effect:
    row = await control.set_record(
        await scope.context("exchange_rate_create"),
        "exchange_rate",
        {},
        {
            "base_currency_id": command.base_currency_id,
            "quote_currency_id": command.quote_currency_id,
            "market_entity_id": command.market_id,
            "rate": command.rate,
            "spread_pct": command.spread_pct,
            "convertible": command.convertible,
        },
    )
    return Effect("The rate is set.", values={"record_id": getattr(row, "id", 0)})


@player_action("exchange_rate:edit", ActionKind.EDIT_RECORD)
async def exchange_rate_edit(scope: PlayerScope, command: ExchangeRateEdit) -> Effect:
    await control.edit_record(await scope.context("exchange_rate_edit"), "exchange_rate", command.record_id, command.values, command.release)
    return Effect("The rate is set so.")


@player_action("exchange_rate:delete", ActionKind.EDIT_RECORD)
async def exchange_rate_delete(scope: PlayerScope, command: ExchangeRateTarget) -> Effect:
    await control.delete_record(await scope.context("exchange_rate_delete"), "exchange_rate", command.record_id)
    return Effect("The rate is struck.")


@player_action("bill_of_exchange:create", ActionKind.EDIT_RECORD)
async def bill_of_exchange_create(scope: PlayerScope, command: BillOfExchangeDraft) -> Effect:
    row = await control.set_record(
        await scope.context("bill_of_exchange_create"),
        "bill_of_exchange",
        {},
        {
            "drawer_node_id": command.drawer_id,
            "payee_node_id": command.payee_id,
            "from_entity_id": command.from_id,
            "to_entity_id": command.to_id,
            "amount": command.amount,
        },
    )
    return Effect("The bill is drawn.", values={"record_id": getattr(row, "id", 0)})


@player_action("bill_of_exchange:edit", ActionKind.EDIT_RECORD)
async def bill_of_exchange_edit(scope: PlayerScope, command: BillOfExchangeEdit) -> Effect:
    await control.edit_record(await scope.context("bill_of_exchange_edit"), "bill_of_exchange", command.record_id, command.values, command.release)
    return Effect("The bill is set so.")


@player_action("bill_of_exchange:delete", ActionKind.EDIT_RECORD)
async def bill_of_exchange_delete(scope: PlayerScope, command: BillOfExchangeTarget) -> Effect:
    await control.delete_record(await scope.context("bill_of_exchange_delete"), "bill_of_exchange", command.record_id)
    return Effect("The bill is torn up.")


@player_action("economic_order:create", ActionKind.EDIT_RECORD)
async def economic_order_create(scope: PlayerScope, command: EconomicOrderDraft) -> Effect:
    row = await control.set_record(
        await scope.context("economic_order_create"),
        "economic_order",
        {},
        {
            "polity_entity_id": command.polity_id,
            "sector": command.sector,
            "ownership": command.ownership,
            "allocation": command.allocation,
            "labour": command.labour,
            "distribution": command.distribution,
            "planning_capacity": command.planning_capacity,
        },
    )
    return Effect("The order is set.", values={"record_id": getattr(row, "id", 0)})


@player_action("economic_order:edit", ActionKind.EDIT_RECORD)
async def economic_order_edit(scope: PlayerScope, command: EconomicOrderEdit) -> Effect:
    await control.edit_record(await scope.context("economic_order_edit"), "economic_order", command.record_id, command.values, command.release)
    return Effect("The order is set so.")


@player_action("economic_order:delete", ActionKind.EDIT_RECORD)
async def economic_order_delete(scope: PlayerScope, command: EconomicOrderTarget) -> Effect:
    await control.delete_record(await scope.context("economic_order_delete"), "economic_order", command.record_id)
    return Effect("The order is struck.")


@player_action("economic_order_kind:create", ActionKind.EDIT_RECORD)
async def economic_order_kind_create(scope: PlayerScope, command: EconomicOrderKindDraft) -> Effect:
    row = await control.set_record(
        await scope.context("economic_order_kind_create"),
        "economic_order_kind",
        {},
        {
            "name": command.name,
            "ownership": command.ownership,
            "allocation": command.allocation,
            "labour": command.labour,
            "distribution": command.distribution,
        },
    )
    return Effect("The order is named.", values={"record_id": getattr(row, "id", 0)})


@player_action("economic_order_kind:edit", ActionKind.EDIT_RECORD)
async def economic_order_kind_edit(scope: PlayerScope, command: EconomicOrderKindEdit) -> Effect:
    await control.edit_record(await scope.context("economic_order_kind_edit"), "economic_order_kind", command.record_id, command.values, command.release)
    return Effect("The named order is set so.")


@player_action("economic_order_kind:delete", ActionKind.EDIT_RECORD)
async def economic_order_kind_delete(scope: PlayerScope, command: EconomicOrderKindTarget) -> Effect:
    await control.delete_record(await scope.context("economic_order_kind_delete"), "economic_order_kind", command.record_id)
    return Effect("The named order is struck.")


@player_action("order_transition:create", ActionKind.EDIT_RECORD)
async def order_transition_create(scope: PlayerScope, command: OrderTransitionDraft) -> Effect:
    row = await begin_transition(await scope.context("order_transition_create"), command.polity_id, command.sector, command.kind, command.compensation)
    return Effect("The change of order is proclaimed.", values={"record_id": getattr(row, "id", 0)})


@player_action("order_transition:edit", ActionKind.EDIT_RECORD)
async def order_transition_edit(scope: PlayerScope, command: OrderTransitionEdit) -> Effect:
    await control.edit_record(await scope.context("order_transition_edit"), "order_transition", command.record_id, command.values, command.release)
    return Effect("The change of order is set so.")


@player_action("order_transition:delete", ActionKind.EDIT_RECORD)
async def order_transition_delete(scope: PlayerScope, command: OrderTransitionTarget) -> Effect:
    await control.delete_record(await scope.context("order_transition_delete"), "order_transition", command.record_id)
    return Effect("The change of order is called off.")


@player_action("putting_out:create", ActionKind.EDIT_RECORD)
async def putting_out_create(scope: PlayerScope, command: PuttingOutDraft) -> Effect:
    row = await control.set_record(
        await scope.context("putting_out_create"),
        "putting_out",
        {},
        {
            "merchant_entity_id": command.merchant_id,
            "town_entity_id": command.town_id,
            "raw": command.raw,
            "product": command.product,
            "volume": command.volume,
        },
    )
    return Effect("The work is put out.", values={"record_id": getattr(row, "id", 0)})


@player_action("putting_out:edit", ActionKind.EDIT_RECORD)
async def putting_out_edit(scope: PlayerScope, command: PuttingOutEdit) -> Effect:
    await control.edit_record(await scope.context("putting_out_edit"), "putting_out", command.record_id, command.values, command.release)
    return Effect("The work put out is set so.")


@player_action("putting_out:delete", ActionKind.EDIT_RECORD)
async def putting_out_delete(scope: PlayerScope, command: PuttingOutTarget) -> Effect:
    await control.delete_record(await scope.context("putting_out_delete"), "putting_out", command.record_id)
    return Effect("The work put out is ended.")


@player_action("chain_holding:set", ActionKind.EDIT_RECORD)
async def chain_holding_set(scope: PlayerScope, command: ChainHoldingDraft) -> Effect:
    row = await control.set_record(
        await scope.context("chain_holding_set"),
        "chain_holding",
        {"holder_entity_id": command.holder_id, "town_entity_id": command.town_id, "product": command.product},
        {"share_pct": command.share_pct},
    )
    return Effect("The share is held.", values={"record_id": getattr(row, "id", 0)})


@player_action("chain_holding:edit", ActionKind.EDIT_RECORD)
async def chain_holding_edit(scope: PlayerScope, command: ChainHoldingEdit) -> Effect:
    await control.edit_record(
        await scope.context("chain_holding_edit"), "chain_holding", (command.holder_id, command.town_id, command.product), command.values, command.release
    )
    return Effect("The share is set so.")


@player_action("chain_holding:delete", ActionKind.EDIT_RECORD)
async def chain_holding_delete(scope: PlayerScope, command: ChainHoldingTarget) -> Effect:
    await control.delete_record(await scope.context("chain_holding_delete"), "chain_holding", (command.holder_id, command.town_id, command.product))
    return Effect("The share is sold.")


@player_action("tourist_flow:create", ActionKind.EDIT_RECORD)
async def tourist_flow_create(scope: PlayerScope, command: TouristFlowDraft) -> Effect:
    row = await control.set_record(
        await scope.context("tourist_flow_create"),
        "tourist_flow",
        {},
        {
            "origin_entity_id": command.origin_id,
            "sight_entity_id": command.sight_id,
            "sight": command.sight,
            "visitors": command.visitors,
            "income": command.income,
        },
    )
    return Effect("The travellers set out.", values={"record_id": getattr(row, "id", 0)})


@player_action("tourist_flow:edit", ActionKind.EDIT_RECORD)
async def tourist_flow_edit(scope: PlayerScope, command: TouristFlowEdit) -> Effect:
    await control.edit_record(await scope.context("tourist_flow_edit"), "tourist_flow", command.record_id, command.values, command.release)
    return Effect("The flow of travellers is set so.")


@player_action("tourist_flow:delete", ActionKind.EDIT_RECORD)
async def tourist_flow_delete(scope: PlayerScope, command: TouristFlowTarget) -> Effect:
    await control.delete_record(await scope.context("tourist_flow_delete"), "tourist_flow", command.record_id)
    return Effect("The flow of travellers is struck.")


@player_action("order_transition:advance", ActionKind.EDIT_RECORD)
async def order_transition_advance(scope: PlayerScope, command: OrderTransitionTarget) -> Effect:
    row = await control.advance_transition(await scope.context("order_transition_advance"), command.record_id)
    return Effect(f"The change of order stands at {spoken(row.stage)}.")


@player_action("orders:run", ActionKind.EDIT_RECORD)
async def orders_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_orders(await scope.context("orders_run"))
    told = [
        several(tally.savings.saved, "household", "households") + " saved",
        several(tally.exchange.rates, "rate", "rates") + " read",
        several(tally.economy.transferred, "holding", "holdings") + " moved by changes of order",
        several(tally.putting_out.worked, "village", "villages") + " worked put-out goods",
        several(tally.tourism.flows, "flow", "flows") + " of travellers",
    ]
    return Effect("; ".join(told) + ".")
