from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.monetary import MonetaryAim

RATE_MAX = 100


class MonetaryAuthorityRow(Base):
    __tablename__ = "monetary_authorities"
    __table_args__ = (
        between("independence", PERCENT_MIN, PERCENT_MAX),
        between("rate", 0, RATE_MAX),
        between("effective_rate", 0, RATE_MAX),
        between("reserve_requirement_pct", PERCENT_MIN, PERCENT_MAX),
        at_least("reserves", 0),
        at_least("peg_reserves", 0),
        at_least("founded_epoch", 0),
        Index("ix_monetary_authorities_holder", "holder_node_id"),
        Index("ix_monetary_authorities_issuer", "issuer_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id", ondelete="CASCADE"), unique=True)
    holder_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    issuer_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    coin_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    independence: Mapped[int] = mapped_column(default=0)
    aim: Mapped[MonetaryAim] = mapped_column(enum_type(MonetaryAim, "aim"), default=MonetaryAim.STABLE_VALUE)
    rate: Mapped[int] = mapped_column(default=5)
    effective_rate: Mapped[int] = mapped_column(default=5)
    reserve_requirement_pct: Mapped[int] = mapped_column(default=10)
    peg_currency_id: Mapped[int | None] = mapped_column(ForeignKey("currencies.id", ondelete="SET NULL"))
    peg_good: Mapped[CommodityKind | None] = mapped_column(enum_type(CommodityKind, "peg_good"))
    lender_of_last_resort: Mapped[bool] = mapped_column(default=False)
    reserves: Mapped[int] = mapped_column(default=0)
    peg_reserves: Mapped[int] = mapped_column(default=0)
    peg_broken_epoch: Mapped[int | None]
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MonetaryRateRow(Base):
    __tablename__ = "monetary_rates"
    __table_args__ = (
        between("rate", 0, RATE_MAX),
        at_least("epoch", 0),
        Index("ix_monetary_rates_authority", "authority_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    authority_id: Mapped[int] = mapped_column(ForeignKey("monetary_authorities.id", ondelete="CASCADE"))
    epoch: Mapped[int] = mapped_column(default=0)
    rate: Mapped[int] = mapped_column(default=0)
    aim: Mapped[MonetaryAim] = mapped_column(enum_type(MonetaryAim, "aim"), default=MonetaryAim.STABLE_VALUE)
    supply: Mapped[int] = mapped_column(default=0)
    trust: Mapped[int] = mapped_column(default=0)
