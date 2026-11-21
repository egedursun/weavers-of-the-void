from sqlalchemy import JSON, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.competition import CartelAim, MarketForm, PriceWarOutcome
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN


class MarketStructureRow(Base):
    __tablename__ = "market_structures"
    __table_args__ = (
        UniqueConstraint("market_entity_id", "commodity", name="uq_market_structures_good"),
        between("concentration", PERCENT_MIN, PERCENT_MAX),
        between("small_sellers_pct", PERCENT_MIN, PERCENT_MAX),
        at_least("updated_epoch", 0),
        Index("ix_market_structures_market", "market_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    market_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    commodity: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "commodity"))
    sellers: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    small_sellers_pct: Mapped[int] = mapped_column(default=0)
    concentration: Mapped[int] = mapped_column(default=0)
    form: Mapped[MarketForm] = mapped_column(enum_type(MarketForm, "form"), default=MarketForm.MANY_SELLERS)
    barriers: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CartelRow(Base):
    __tablename__ = "cartels"
    __table_args__ = (
        at_least("agreed_price", 0),
        at_least("quota", 0),
        between("secrecy", PERCENT_MIN, PERCENT_MAX),
        between("discipline", PERCENT_MIN, PERCENT_MAX),
        at_least("formed_epoch", 0),
        Index("ix_cartels_commodity", "commodity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    leader_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    members: Mapped[list[int]] = mapped_column(JSON, default=list)
    markets: Mapped[list[int]] = mapped_column(JSON, default=list)
    commodity: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "commodity"))
    aim: Mapped[CartelAim] = mapped_column(enum_type(CartelAim, "aim"), default=CartelAim.PRICE)
    agreed_price: Mapped[int] = mapped_column(default=0)
    quota: Mapped[int] = mapped_column(default=0)
    secrecy: Mapped[int] = mapped_column(default=60)
    discipline: Mapped[int] = mapped_column(default=70)
    exposed: Mapped[bool] = mapped_column(default=False)
    formed_epoch: Mapped[int] = mapped_column(default=0)
    broken_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PriceWarRow(Base):
    __tablename__ = "price_wars"
    __table_args__ = (
        between("cut_pct", PERCENT_MIN, PERCENT_MAX),
        at_least("losses", 0),
        at_least("started_epoch", 0),
        Index("ix_price_wars_market", "market_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    aggressor_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    targets: Mapped[list[int]] = mapped_column(JSON, default=list)
    market_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    commodity: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "commodity"))
    cut_pct: Mapped[int] = mapped_column(default=20)
    losses: Mapped[int] = mapped_column(default=0)
    outcome: Mapped[PriceWarOutcome] = mapped_column(enum_type(PriceWarOutcome, "outcome"), default=PriceWarOutcome.ONGOING)
    started_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
