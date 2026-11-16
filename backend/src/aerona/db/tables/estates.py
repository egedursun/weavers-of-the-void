from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.faction import EstatePrivilege, MovementCause
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.made import CompanyCharter
from aerona.domain.enums.society import SocialClass


class EstateProfileRow(Base):
    __tablename__ = "estate_profiles"
    __table_args__ = (
        between("loyalty", PERCENT_MIN, PERCENT_MAX),
        between("influence", PERCENT_MIN, PERCENT_MAX),
        Index("ix_estate_profiles_polity", "polity_entity_id"),
    )

    faction_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    social_class: Mapped[SocialClass] = mapped_column(enum_type(SocialClass, "social_class"))
    loyalty: Mapped[int] = mapped_column(default=50)
    influence: Mapped[int] = mapped_column(default=10)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class EstatePrivilegeRow(Base):
    __tablename__ = "estate_privileges"
    __table_args__ = (at_least("granted_epoch", 0),)

    estate_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    privilege: Mapped[EstatePrivilege] = mapped_column(enum_type(EstatePrivilege, "privilege"), primary_key=True)
    granted_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[bool] = mapped_column(default=False)


class MovementProfileRow(Base):
    __tablename__ = "movement_profiles"
    __table_args__ = (between("support", PERCENT_MIN, PERCENT_MAX), Index("ix_movement_profiles_polity", "polity_entity_id"))

    faction_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    cause: Mapped[MovementCause] = mapped_column(enum_type(MovementCause, "cause"))
    polity_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    target_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    support: Mapped[int] = mapped_column(default=0)
    is_party: Mapped[bool] = mapped_column(default=False)
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MovementSupportRow(Base):
    __tablename__ = "movement_support"
    __table_args__ = (between("share", PERCENT_MIN, PERCENT_MAX),)

    movement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True, index=True)
    share: Mapped[int] = mapped_column(default=0)
    locked: Mapped[bool] = mapped_column(default=False)


class CompanyProfileRow(Base):
    __tablename__ = "company_profiles"
    __table_args__ = (between("dividend_pct", PERCENT_MIN, PERCENT_MAX), at_least("chartered_epoch", 0))

    faction_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    polity_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    route_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    region_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    commodity: Mapped[CommodityKind | None] = mapped_column(enum_type(CommodityKind, "commodity"))
    dividend_pct: Mapped[int] = mapped_column(default=30)
    value: Mapped[int] = mapped_column(default=0)
    chartered_epoch: Mapped[int] = mapped_column(default=0)
    charter: Mapped[CompanyCharter] = mapped_column(enum_type(CompanyCharter, "charter"), default=CompanyCharter.CHARTERED)
    headquarters_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CompanyShareRow(Base):
    __tablename__ = "company_shares"
    __table_args__ = (between("share", PERCENT_MIN, PERCENT_MAX),)

    company_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True, index=True)
    share: Mapped[int] = mapped_column(default=10)
    locked: Mapped[bool] = mapped_column(default=False)


class HolyOrderProfileRow(Base):
    __tablename__ = "holy_order_profiles"
    __table_args__ = (between("tithe_share", PERCENT_MIN, PERCENT_MAX),)

    faction_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    cult_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    fortress_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    tithe_share: Mapped[int] = mapped_column(default=10)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class GuildSecretRow(Base):
    __tablename__ = "guild_secrets"
    __table_args__ = (at_least("since_epoch", 0),)

    guild_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    technique: Mapped[Technique] = mapped_column(enum_type(Technique, "technique"), primary_key=True)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[bool] = mapped_column(default=False)
