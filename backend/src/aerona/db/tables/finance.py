from sqlalchemy import JSON, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.finance import CreditState, SpeculationStatus, TradePolicyKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN


class TradePolicyRow(Base):
    __tablename__ = "trade_policies"
    __table_args__ = (between("rate_pct", PERCENT_MIN, PERCENT_MAX), at_least("since_epoch", 0), Index("ix_trade_policies_issuer", "issuer_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    issuer_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[TradePolicyKind] = mapped_column(enum_type(TradePolicyKind, "kind"))
    commodity: Mapped[CommodityKind | None] = mapped_column(enum_type(CommodityKind, "commodity"))
    partner_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    rate_pct: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int]
    reason: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CreditProfileRow(Base):
    __tablename__ = "credit_profiles"
    __table_args__ = (
        between("rating", PERCENT_MIN, PERCENT_MAX),
        between("interest_pct", PERCENT_MIN, PERCENT_MAX),
        at_least("reserves", 0),
        at_least("defaults", 0),
        at_least("epoch", 0),
    )

    subject_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    rating: Mapped[int] = mapped_column(default=50)
    state: Mapped[CreditState] = mapped_column(enum_type(CreditState, "state"), default=CreditState.NORMAL)
    interest_pct: Mapped[int] = mapped_column(default=10)
    reserves: Mapped[int] = mapped_column(default=0)
    defaults: Mapped[int] = mapped_column(default=0)
    restructured_until: Mapped[int | None]
    epoch: Mapped[int]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SpeculationRow(Base):
    __tablename__ = "speculations"
    __table_args__ = (
        at_least("units", 0),
        at_least("price", 0),
        at_least("opened_epoch", 0),
        Index("ix_speculations_merchant", "merchant_node_id"),
        Index("ix_speculations_market", "market_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    market_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    commodity: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "commodity"))
    units: Mapped[int] = mapped_column(default=0)
    price: Mapped[int] = mapped_column(default=0)
    status: Mapped[SpeculationStatus] = mapped_column(enum_type(SpeculationStatus, "status"), default=SpeculationStatus.HOARDING)
    opened_epoch: Mapped[int]
    settled_epoch: Mapped[int | None]
    gain: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class EconomicIndicatorRow(Base):
    __tablename__ = "economic_indicators"
    __table_args__ = (
        at_least("epoch", 0),
        at_least("output", 0),
        at_least("price_index", 0),
        at_least("debt_ratio", 0),
        between("unemployment", PERCENT_MIN, PERCENT_MAX),
        between("market_access", PERCENT_MIN, PERCENT_MAX),
        at_least("black_market", 0),
        UniqueConstraint("subject_node_id", "epoch", name="uq_economic_indicators_subject_epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    epoch: Mapped[int]
    output: Mapped[int] = mapped_column(default=0)
    price_index: Mapped[int] = mapped_column(default=100)
    trade_balance: Mapped[int] = mapped_column(default=0)
    treasury: Mapped[int] = mapped_column(default=0)
    debt_ratio: Mapped[int] = mapped_column(default=0)
    unemployment: Mapped[int] = mapped_column(default=0)
    market_access: Mapped[int] = mapped_column(default=100)
    black_market: Mapped[int] = mapped_column(default=0)
    living: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
