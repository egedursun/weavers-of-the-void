from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.securities import SecurityKind

MOOD_MIN = -100
MOOD_MAX = 100


class StockExchangeRow(Base):
    __tablename__ = "stock_exchanges"
    __table_args__ = (
        at_least("listing_fee", 0),
        between("margin_pct", PERCENT_MIN, PERCENT_MAX),
        between("mood", MOOD_MIN, MOOD_MAX),
        at_least("founded_epoch", 0),
        Index("ix_stock_exchanges_settlement", "settlement_entity_id"),
        Index("ix_stock_exchanges_owner", "owner_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    settlement_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    network_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    owner_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    listing_fee: Mapped[int] = mapped_column(default=10)
    margin_pct: Mapped[int] = mapped_column(default=30)
    members: Mapped[list[int]] = mapped_column(JSON, default=list)
    mood: Mapped[int] = mapped_column(default=0)
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class IssuedSecurityRow(Base):
    __tablename__ = "issued_securities"
    __table_args__ = (
        at_least("amount", 0),
        at_least("face_value", 0),
        between("coupon_pct", PERCENT_MIN, PERCENT_MAX),
        at_least("price", 0),
        between("belief", PERCENT_MIN, PERCENT_MAX),
        at_least("listed_epoch", 0),
        Index("ix_issued_securities_issuer", "issuer_node_id"),
        Index("ix_issued_securities_exchange", "exchange_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    issuer_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[SecurityKind] = mapped_column(enum_type(SecurityKind, "kind"), default=SecurityKind.SHARE)
    amount: Mapped[int] = mapped_column(default=100)
    face_value: Mapped[int] = mapped_column(default=10)
    coupon_pct: Mapped[int] = mapped_column(default=0)
    maturity_epoch: Mapped[int | None]
    exchange_id: Mapped[int | None] = mapped_column(ForeignKey("stock_exchanges.id", ondelete="SET NULL"))
    loan_id: Mapped[int | None] = mapped_column(ForeignKey("loans.id", ondelete="SET NULL"))
    price: Mapped[int] = mapped_column(default=10)
    belief: Mapped[int] = mapped_column(default=50)
    bubble: Mapped[bool] = mapped_column(default=False)
    listed_epoch: Mapped[int] = mapped_column(default=0)
    defaulted_epoch: Mapped[int | None]
    delisted_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SecurityHoldingRow(Base):
    __tablename__ = "security_holdings"
    __table_args__ = (
        at_least("amount", 0),
        at_least("bought_price", 0),
        at_least("on_margin", 0),
        Index("ix_security_holdings_holder", "holder_node_id"),
        Index("ix_security_holdings_security", "security_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    security_id: Mapped[int] = mapped_column(ForeignKey("issued_securities.id", ondelete="CASCADE"))
    amount: Mapped[int] = mapped_column(default=0)
    bought_price: Mapped[int] = mapped_column(default=0)
    on_margin: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SecurityPriceRow(Base):
    __tablename__ = "security_prices"
    __table_args__ = (
        at_least("price", 0),
        at_least("volume", 0),
        at_least("epoch", 0),
        Index("ix_security_prices_security", "security_id"),
        Index("ix_security_prices_issuer", "issuer_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    security_id: Mapped[int] = mapped_column(ForeignKey("issued_securities.id", ondelete="CASCADE"))
    issuer_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    epoch: Mapped[int] = mapped_column(default=0)
    price: Mapped[int] = mapped_column(default=0)
    volume: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
