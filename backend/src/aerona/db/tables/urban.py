from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.urban import (
    ConvoyStatus,
    CrimeStance,
    MarketPlay,
    OrderLaw,
    PreservationMethod,
    RacketKind,
    TransportKind,
    TribunalVerdict,
    UrbanService,
)

SERVICE_FIELDS = ("coverage",)
TURF_FIELDS = ("strength",)
RACKET_FIELDS = ("income",)
PAYROLL_FIELDS = ("bribe",)
STANCE_FIELDS = ("strength",)
ORDER_LAW_FIELDS = ("strength",)
TRADING_POST_FIELDS = ("informants", "goods", "owner_entity_id")
CONVOY_FIELDS = ("cargo", "preservation", "animals", "vehicles", "guards", "passengers", "season", "status", "region_entity_id", "capacity")
FLEET_FIELDS = ("count", "age", "condition")
PLAY_FIELDS = ("strength", "until_epoch")


class DistrictServiceRow(Base):
    __tablename__ = "district_services"
    __table_args__ = (between("coverage", PERCENT_MIN, PERCENT_MAX),)

    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"), primary_key=True)
    service: Mapped[UrbanService] = mapped_column(enum_type(UrbanService, "service"), primary_key=True)
    coverage: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TurfRow(Base):
    __tablename__ = "turf"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX), at_least("since_epoch", 0), Index("ix_turf_faction", "faction_entity_id"))

    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"), primary_key=True)
    faction_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    strength: Mapped[int] = mapped_column(default=20)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class RacketRow(Base):
    __tablename__ = "rackets"
    __table_args__ = (at_least("income", 0), at_least("since_epoch", 0), Index("ix_rackets_settlement", "settlement_entity_id"))

    faction_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    racket: Mapped[RacketKind] = mapped_column(enum_type(RacketKind, "racket"), primary_key=True)
    income: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PayrollRow(Base):
    __tablename__ = "crime_payroll"
    __table_args__ = (at_least("bribe", 0), at_least("since_epoch", 0))

    faction_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    official_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    bribe: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CrimeStanceRow(Base):
    __tablename__ = "crime_stances"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX), at_least("since_epoch", 0))

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    faction_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    stance: Mapped[CrimeStance] = mapped_column(enum_type(CrimeStance, "stance"))
    strength: Mapped[int] = mapped_column(default=50)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class OrderLawRow(Base):
    __tablename__ = "order_laws"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX),)

    faction_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    law: Mapped[OrderLaw] = mapped_column(enum_type(OrderLaw, "law"), primary_key=True)
    strength: Mapped[int] = mapped_column(default=60)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TribunalRow(Base):
    __tablename__ = "order_tribunals"
    __table_args__ = (at_least("epoch", 0), at_least("fine", 0), Index("ix_order_tribunals_faction", "faction_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    faction_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    accused_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    law: Mapped[OrderLaw] = mapped_column(enum_type(OrderLaw, "law"))
    verdict: Mapped[TribunalVerdict] = mapped_column(enum_type(TribunalVerdict, "verdict"))
    fine: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)


class TradingPostRow(Base):
    __tablename__ = "trading_posts"
    __table_args__ = (at_least("informants", 0), at_least("goods", 0), at_least("since_epoch", 0), Index("ix_trading_posts_owner", "owner_entity_id"))

    structure_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    owner_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    host_settlement_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    informants: Mapped[int] = mapped_column(default=0)
    goods: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ConvoyRow(Base):
    __tablename__ = "convoys"
    __table_args__ = (
        at_least("animals", 0),
        at_least("vehicles", 0),
        at_least("guards", 0),
        at_least("capacity", 0),
        at_least("departed_epoch", 0),
        Index("ix_convoys_route", "route_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    route_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    cargo: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    preservation: Mapped[PreservationMethod] = mapped_column(enum_type(PreservationMethod, "preservation"), default=PreservationMethod.NONE)
    animals: Mapped[int] = mapped_column(default=0)
    vehicles: Mapped[int] = mapped_column(default=0)
    guards: Mapped[int] = mapped_column(default=0)
    passengers: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    season: Mapped[int] = mapped_column(default=0)
    status: Mapped[ConvoyStatus] = mapped_column(enum_type(ConvoyStatus, "status"), default=ConvoyStatus.LOADING)
    region_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    capacity: Mapped[int] = mapped_column(default=0)
    departed_epoch: Mapped[int] = mapped_column(default=0)
    arrived_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class FleetRow(Base):
    __tablename__ = "transport_fleets"
    __table_args__ = (at_least("count", 0), at_least("age", 0), between("condition", PERCENT_MIN, PERCENT_MAX))

    owner_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[TransportKind] = mapped_column(enum_type(TransportKind, "kind"), primary_key=True)
    count: Mapped[int] = mapped_column(default=0)
    age: Mapped[int] = mapped_column(default=0)
    condition: Mapped[int] = mapped_column(default=100)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MarketPlayRow(Base):
    __tablename__ = "market_plays"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX), at_least("since_epoch", 0), Index("ix_market_plays_settlement", "settlement_entity_id"))

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    commodity: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "commodity"), primary_key=True)
    play: Mapped[MarketPlay] = mapped_column(enum_type(MarketPlay, "play"), primary_key=True)
    strength: Mapped[int] = mapped_column(default=50)
    since_epoch: Mapped[int] = mapped_column(default=0)
    until_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
