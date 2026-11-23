from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type, nullable_between
from aerona.db.profile_guard import register_profile_table
from aerona.domain.enums.demography import Job
from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import DriftCause, LabourReason, MobilityEvent, ShortfallEffect

WIDE_PCT = PERCENT_MAX * 10


class CommunityNeedRow(Base):
    __tablename__ = "community_needs"
    __table_args__ = (
        at_least("wanted", 0),
        at_least("got", 0),
        nullable_between("held_pct", PERCENT_MIN, PERCENT_MAX),
        Index("ix_community_needs_community", "community_entity_id"),
    )

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    social_class: Mapped[SocialClass] = mapped_column(enum_type(SocialClass, "social_class"), primary_key=True)
    commodity: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "commodity"), primary_key=True)
    wanted: Mapped[int] = mapped_column(default=0)
    got: Mapped[int] = mapped_column(default=0)
    held_pct: Mapped[int | None]
    epoch: Mapped[int] = mapped_column(default=0)


class CommunityShortfallRow(Base):
    __tablename__ = "community_shortfalls"
    __table_args__ = (between("short_pct", PERCENT_MIN, PERCENT_MAX), Index("ix_community_shortfalls_community", "community_entity_id"))

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    effect: Mapped[ShortfallEffect] = mapped_column(enum_type(ShortfallEffect, "effect"), primary_key=True)
    short_pct: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ClassStandingRow(Base):
    __tablename__ = "class_standing"
    __table_args__ = (
        between("fed_pct", PERCENT_MIN, PERCENT_MAX),
        between("needs_met_pct", PERCENT_MIN, PERCENT_MAX),
        between("luxury_pct", PERCENT_MIN, WIDE_PCT),
        at_least("wealth", 0),
        Index("ix_class_standing_community", "community_entity_id"),
    )

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    social_class: Mapped[SocialClass] = mapped_column(enum_type(SocialClass, "social_class"), primary_key=True)
    fed_pct: Mapped[int] = mapped_column(default=PERCENT_MAX)
    needs_met_pct: Mapped[int] = mapped_column(default=PERCENT_MAX)
    luxury_pct: Mapped[int] = mapped_column(default=PERCENT_MAX)
    wealth: Mapped[int] = mapped_column(default=0)
    income: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LabourReasonRow(Base):
    __tablename__ = "labour_reasons"
    __table_args__ = (at_least("price_pct", 0), Index("ix_labour_reasons_community", "community_entity_id"))

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    job: Mapped[Job] = mapped_column(enum_type(Job, "job"), primary_key=True)
    reason: Mapped[LabourReason] = mapped_column(enum_type(LabourReason, "reason"), primary_key=True)
    workers: Mapped[int] = mapped_column(default=0)
    commodity: Mapped[CommodityKind | None] = mapped_column(enum_type(CommodityKind, "commodity"))
    workshop: Mapped[WorkshopKind | None] = mapped_column(enum_type(WorkshopKind, "workshop"))
    price_pct: Mapped[int] = mapped_column(default=PERCENT_MAX)
    epoch: Mapped[int] = mapped_column(default=0)


class DriftCauseRow(Base):
    __tablename__ = "culture_drift_causes"
    __table_args__ = (Index("ix_culture_drift_causes_community", "community_entity_id"),)

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    cause: Mapped[DriftCause] = mapped_column(enum_type(DriftCause, "cause"), primary_key=True)
    axis: Mapped[ValueAxis] = mapped_column(enum_type(ValueAxis, "axis"), primary_key=True)
    amount: Mapped[int] = mapped_column(default=0)
    total: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)


class DriftImpositionRow(Base):
    __tablename__ = "drift_impositions"
    __table_args__ = (at_least("epochs_left", 1), between("amount", -PERCENT_MAX, PERCENT_MAX), Index("ix_drift_impositions_community", "community_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    cause: Mapped[DriftCause] = mapped_column(enum_type(DriftCause, "cause"))
    axis: Mapped[ValueAxis] = mapped_column(enum_type(ValueAxis, "axis"))
    amount: Mapped[int]
    epochs_left: Mapped[int] = mapped_column(default=1)
    created_epoch: Mapped[int] = mapped_column(default=0)


class PolityLoyaltyRow(Base):
    __tablename__ = "polity_loyalty"
    __table_args__ = (
        between("loyalty", PERCENT_MIN, PERCENT_MAX),
        at_least("value_distance", 0),
        at_least("grievances", 0),
        at_least("benefits", 0),
        Index("ix_polity_loyalty_member", "member_entity_id"),
    )

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    member_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    value_distance: Mapped[int] = mapped_column(default=0)
    grievances: Mapped[int] = mapped_column(default=0)
    benefits: Mapped[int] = mapped_column(default=0)
    satisfaction: Mapped[int] = mapped_column(default=0)
    loyalty: Mapped[int] = mapped_column(default=PERCENT_MAX // 2)
    parts: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MobilityEventRow(Base):
    __tablename__ = "mobility_events"
    __table_args__ = (at_least("count", 0), at_least("epoch", 0), Index("ix_mobility_events_community", "community_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    community_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    event: Mapped[MobilityEvent] = mapped_column(enum_type(MobilityEvent, "event"))
    count: Mapped[int] = mapped_column(default=0)
    mortal_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    house_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    other_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    by_hand: Mapped[bool] = mapped_column(default=False)
    epoch: Mapped[int] = mapped_column(default=0)


class CorveeRow(Base):
    __tablename__ = "corvee_levies"
    __table_args__ = (between("share_pct", PERCENT_MIN, PERCENT_MAX), at_least("since_epoch", 0))

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    share_pct: Mapped[int] = mapped_column(default=0)
    polity_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    work_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    laboured_epochs: Mapped[int] = mapped_column(default=0, server_default="0")
    since_epoch: Mapped[int] = mapped_column(default=0)
    by_hand: Mapped[bool] = mapped_column(default=True)


register_profile_table(ClassStandingRow.__tablename__, "community_entity_id")
register_profile_table(PolityLoyaltyRow.__tablename__, "member_entity_id")
