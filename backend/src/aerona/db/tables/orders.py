from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
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
    TransitionStage,
)

SAVING_FIELDS = ("share_pct", "form", "saved", "land", "goods")
HOARD_FIELDS = ("holder_node_id", "place_entity_id", "amount", "state", "found_by_node_id", "hidden_epoch", "found_epoch")
RATE_FIELDS = ("rate", "spread_pct", "changer_node_id", "convertible", "volume")
BILL_FIELDS = ("drawer_node_id", "payee_node_id", "from_entity_id", "to_entity_id", "amount", "settled")
ORDER_FIELDS = ("sector", "ownership", "allocation", "labour", "distribution", "planning_capacity", "kind_id")
ORDER_KIND_FIELDS = ("name", "ownership", "allocation", "labour", "distribution")
TRANSITION_FIELDS = ("kind", "stage", "compensation", "resistance", "transferred", "ended_epoch")
PUTTING_OUT_FIELDS = ("town_entity_id", "raw", "product", "volume", "active")
CHAIN_FIELDS = ("share_pct",)
TOURISM_FIELDS = ("sight", "visitors", "income")
AXES = ("ownership", "allocation", "labour", "distribution")


class SavingRow(Base):
    __tablename__ = "savings"
    __table_args__ = (between("share_pct", PERCENT_MIN, PERCENT_MAX), at_least("saved", 0))

    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"), primary_key=True)
    share_pct: Mapped[int] = mapped_column(default=10)
    form: Mapped[SavingForm] = mapped_column(enum_type(SavingForm, "form"), default=SavingForm.HOARD)
    saved: Mapped[int] = mapped_column(default=0)
    land: Mapped[int] = mapped_column(default=0, server_default="0")
    goods: Mapped[int] = mapped_column(default=0, server_default="0")
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class HoardRow(Base):
    __tablename__ = "hoards"
    __table_args__ = (at_least("amount", 0), at_least("hidden_epoch", 0), Index("ix_hoards_place", "place_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    place_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    amount: Mapped[int] = mapped_column(default=0)
    state: Mapped[HoardState] = mapped_column(enum_type(HoardState, "state"), default=HoardState.HIDDEN)
    hidden_epoch: Mapped[int] = mapped_column(default=0)
    found_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    found_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ExchangeRateRow(Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        at_least("rate", 1),
        at_least("volume", 0),
        between("spread_pct", PERCENT_MIN, PERCENT_MAX),
        Index("ix_exchange_rates_pair", "base_currency_id", "quote_currency_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    base_currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id", ondelete="CASCADE"))
    quote_currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id", ondelete="CASCADE"))
    market_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    rate: Mapped[int] = mapped_column(default=100)
    spread_pct: Mapped[int] = mapped_column(default=4)
    changer_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    convertible: Mapped[bool] = mapped_column(default=True)
    volume: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class BillOfExchangeRow(Base):
    __tablename__ = "bills_of_exchange"
    __table_args__ = (at_least("amount", 0), at_least("issued_epoch", 0))

    id: Mapped[int] = mapped_column(primary_key=True)
    drawer_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    payee_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    from_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    to_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    amount: Mapped[int] = mapped_column(default=0)
    issued_epoch: Mapped[int] = mapped_column(default=0)
    settled: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class EconomicOrderKindRow(Base):
    __tablename__ = "economic_order_kinds"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    ownership: Mapped[OwnershipRegime] = mapped_column(enum_type(OwnershipRegime, "ownership"))
    allocation: Mapped[AllocationMode] = mapped_column(enum_type(AllocationMode, "allocation"))
    labour: Mapped[OrderLabour] = mapped_column(enum_type(OrderLabour, "labour"))
    distribution: Mapped[DistributionRule] = mapped_column(enum_type(DistributionRule, "distribution"))
    built_in: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class EconomicOrderRow(Base):
    __tablename__ = "economic_orders"
    __table_args__ = (
        between("planning_capacity", PERCENT_MIN, PERCENT_MAX),
        at_least("since_epoch", 0),
        Index("ix_economic_orders_polity", "polity_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    sector: Mapped[CommodityKind | None] = mapped_column(enum_type(CommodityKind, "sector"))
    ownership: Mapped[OwnershipRegime] = mapped_column(enum_type(OwnershipRegime, "ownership"), default=OwnershipRegime.HOUSEHOLD)
    allocation: Mapped[AllocationMode] = mapped_column(enum_type(AllocationMode, "allocation"), default=AllocationMode.MARKET)
    labour: Mapped[OrderLabour] = mapped_column(enum_type(OrderLabour, "labour"), default=OrderLabour.FREE)
    distribution: Mapped[DistributionRule] = mapped_column(enum_type(DistributionRule, "distribution"), default=DistributionRule.BY_HOLDING)
    planning_capacity: Mapped[int] = mapped_column(default=30)
    kind_id: Mapped[int | None] = mapped_column(ForeignKey("economic_order_kinds.id", ondelete="SET NULL"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class OrderTransitionRow(Base):
    __tablename__ = "order_transitions"
    __table_args__ = (between("resistance", PERCENT_MIN, PERCENT_MAX), at_least("started_epoch", 0), Index("ix_order_transitions_polity", "polity_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    sector: Mapped[CommodityKind | None] = mapped_column(enum_type(CommodityKind, "sector"))
    kind: Mapped[TransitionKind] = mapped_column(enum_type(TransitionKind, "kind"))
    from_axes: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    to_axes: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    stage: Mapped[TransitionStage] = mapped_column(enum_type(TransitionStage, "stage"), default=TransitionStage.PROCLAIMED)
    compensation: Mapped[Compensation] = mapped_column(enum_type(Compensation, "compensation"), default=Compensation.NONE)
    resistance: Mapped[int] = mapped_column(default=0)
    transferred: Mapped[int] = mapped_column(default=0)
    started_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PuttingOutRow(Base):
    __tablename__ = "putting_out"
    __table_args__ = (at_least("volume", 0), at_least("since_epoch", 0), Index("ix_putting_out_town", "town_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    town_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    raw: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "raw"))
    product: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "product"))
    volume: Mapped[int] = mapped_column(default=10)
    active: Mapped[bool] = mapped_column(default=True)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ChainHoldingRow(Base):
    __tablename__ = "chain_holdings"
    __table_args__ = (between("share_pct", PERCENT_MIN, PERCENT_MAX), at_least("since_epoch", 0))

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    town_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    product: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "product"), primary_key=True)
    share_pct: Mapped[int] = mapped_column(default=20)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TouristFlowRow(Base):
    __tablename__ = "tourist_flows"
    __table_args__ = (at_least("visitors", 0), at_least("income", 0), Index("ix_tourist_flows_sight", "sight_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    origin_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    sight_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    sight: Mapped[TouristSight] = mapped_column(enum_type(TouristSight, "sight"))
    visitors: Mapped[int] = mapped_column(default=0)
    income: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
