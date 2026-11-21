from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.kin_dynamics import DisownReason, RivalryCause
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN


class KinDynamicRow(Base):
    __tablename__ = "kin_dynamics"
    __table_args__ = (between("tension", PERCENT_MIN, PERCENT_MAX), Index("ix_kin_dynamics_house", "house_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int | None] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"), index=True)
    house_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    tension: Mapped[int] = mapped_column(default=0)
    formed_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class KinFavourRow(Base):
    __tablename__ = "kin_favours"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX), Index("ix_kin_favours_parent", "parent_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    dynamic_id: Mapped[int] = mapped_column(ForeignKey("kin_dynamics.id", ondelete="CASCADE"), index=True)
    parent_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    child_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    strength: Mapped[int] = mapped_column(default=50)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class KinRivalryRow(Base):
    __tablename__ = "kin_rivalries"
    __table_args__ = (between("heat", PERCENT_MIN, PERCENT_MAX), Index("ix_kin_rivalries_first", "first_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    dynamic_id: Mapped[int] = mapped_column(ForeignKey("kin_dynamics.id", ondelete="CASCADE"), index=True)
    first_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    second_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    cause: Mapped[RivalryCause] = mapped_column(enum_type(RivalryCause, "cause"), default=RivalryCause.FAVOUR)
    heat: Mapped[int] = mapped_column(default=20)
    since_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class KinDisowningRow(Base):
    __tablename__ = "kin_disownings"
    __table_args__ = (Index("ix_kin_disownings_disowned", "disowned_node_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    dynamic_id: Mapped[int] = mapped_column(ForeignKey("kin_dynamics.id", ondelete="CASCADE"), index=True)
    disowner_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    disowned_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    reason: Mapped[DisownReason] = mapped_column(enum_type(DisownReason, "reason"), default=DisownReason.DISOBEDIENCE)
    reversible: Mapped[bool] = mapped_column(default=True)
    epoch: Mapped[int] = mapped_column(default=0)
    reconciled_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class KinBlendRow(Base):
    __tablename__ = "kin_blends"
    __table_args__ = (between("standing", PERCENT_MIN, PERCENT_MAX), Index("ix_kin_blends_member", "member_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    dynamic_id: Mapped[int] = mapped_column(ForeignKey("kin_dynamics.id", ondelete="CASCADE"), index=True)
    member_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    joined_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    standing: Mapped[int] = mapped_column(default=50)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ElderSwayRow(Base):
    __tablename__ = "elder_sway"
    __table_args__ = (between("sway", PERCENT_MIN, PERCENT_MAX), at_least("since_epoch", 0), Index("ix_elder_sway_elder", "elder_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    dynamic_id: Mapped[int] = mapped_column(ForeignKey("kin_dynamics.id", ondelete="CASCADE"), index=True)
    elder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    sway: Mapped[int] = mapped_column(default=60)
    since_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
