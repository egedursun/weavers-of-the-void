from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.genetics import DwellingKind, HouseholdDecision, HouseholdRole
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.society import SocialClass

HOUSEHOLD_FIELDS = ("wealth", "income", "expenses", "servants", "dependents", "burden")


class HouseholdRow(Base):
    __tablename__ = "households"
    __table_args__ = (
        at_least("wealth", 0),
        at_least("income", 0),
        at_least("expenses", 0),
        at_least("servants", 0),
        at_least("dependents", 0),
        between("burden", PERCENT_MIN, PERCENT_MAX),
        at_least("formed_epoch", 0),
        Index("ix_households_settlement", "settlement_node_id"),
        Index("ix_households_head", "head_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    head_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    settlement_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    social_class: Mapped[SocialClass | None] = mapped_column(enum_type(SocialClass, "social_class"))
    wealth: Mapped[int] = mapped_column(default=0)
    income: Mapped[int] = mapped_column(default=0)
    expenses: Mapped[int] = mapped_column(default=0)
    servants: Mapped[int] = mapped_column(default=0)
    dependents: Mapped[int] = mapped_column(default=0)
    burden: Mapped[int] = mapped_column(default=0)
    debts: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    last_decision: Mapped[HouseholdDecision | None] = mapped_column(enum_type(HouseholdDecision, "last_decision"))
    decided_epoch: Mapped[int | None]
    formed_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class HouseholdMemberRow(Base):
    __tablename__ = "household_members"
    __table_args__ = (at_least("joined_epoch", 0), Index("ix_household_members_household", "household_id"))

    member_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    role: Mapped[HouseholdRole] = mapped_column(enum_type(HouseholdRole, "role"))
    cares_for_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    joined_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[bool] = mapped_column(default=False)


class DwellingRow(Base):
    __tablename__ = "dwellings"
    __table_args__ = (
        between("quality", PERCENT_MIN, PERCENT_MAX),
        at_least("rooms", 1),
        at_least("built_epoch", 0),
        Index("ix_dwellings_household", "household_id", unique=True),
        Index("ix_dwellings_settlement", "settlement_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    kind: Mapped[DwellingKind] = mapped_column(enum_type(DwellingKind, "kind"))
    quality: Mapped[int] = mapped_column(default=40)
    rooms: Mapped[int] = mapped_column(default=1)
    settlement_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    district_id: Mapped[int | None] = mapped_column(ForeignKey("districts.id", ondelete="SET NULL"))
    built_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DwellingFurnishingRow(Base):
    __tablename__ = "dwelling_furnishings"
    __table_args__ = (at_least("placed_epoch", 0),)

    item_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    dwelling_id: Mapped[int] = mapped_column(ForeignKey("dwellings.id", ondelete="CASCADE"), index=True)
    placed_epoch: Mapped[int] = mapped_column(default=0)


class HouseholdAggregateRow(Base):
    __tablename__ = "household_aggregates"
    __table_args__ = (
        at_least("households", 0),
        at_least("mean_size", 0),
        between("quality", PERCENT_MIN, PERCENT_MAX),
        at_least("wealth", 0),
        at_least("epoch", 0),
    )

    community_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    social_class: Mapped[SocialClass] = mapped_column(enum_type(SocialClass, "social_class"), primary_key=True)
    households: Mapped[int] = mapped_column(default=0)
    mean_size: Mapped[int] = mapped_column(default=0)
    dwelling_kind: Mapped[DwellingKind] = mapped_column(enum_type(DwellingKind, "dwelling_kind"), default=DwellingKind.HUT)
    quality: Mapped[int] = mapped_column(default=30)
    wealth: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
