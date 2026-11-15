from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.means import ContainerKind, LockKind, NavigationAid, WaterLift, WritingMedium

WRITING_CUSTOM_FIELDS = ("medium",)
WRITTEN_FIELDS = ("medium", "condition", "copies")
SECURITY_FIELDS = ("lock", "lock_quality", "sealed", "guards", "traps", "thwarted")
WATER_LIFT_FIELDS = ("count",)
NAVIGATION_FIELDS = ("quality",)
CONTAINER_FIELDS = ("count", "broken")


class WritingCustomRow(Base):
    __tablename__ = "writing_customs"
    __table_args__ = (at_least("since_epoch", 0),)

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    medium: Mapped[WritingMedium] = mapped_column(enum_type(WritingMedium, "medium"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class WrittenWorkRow(Base):
    __tablename__ = "written_works"
    __table_args__ = (between("condition", PERCENT_MIN, PERCENT_MAX), at_least("copies", 0), at_least("written_epoch", 0))

    work_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    medium: Mapped[WritingMedium] = mapped_column(enum_type(WritingMedium, "medium"))
    condition: Mapped[int] = mapped_column(default=100)
    copies: Mapped[int] = mapped_column(default=1)
    written_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SecurityRow(Base):
    __tablename__ = "securities"
    __table_args__ = (between("lock_quality", PERCENT_MIN, PERCENT_MAX), at_least("guards", 0), at_least("since_epoch", 0))

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    lock: Mapped[LockKind | None] = mapped_column(enum_type(LockKind, "lock"))
    lock_quality: Mapped[int] = mapped_column(default=0)
    sealed: Mapped[bool] = mapped_column(default=False)
    guards: Mapped[int] = mapped_column(default=0)
    traps: Mapped[bool] = mapped_column(default=False)
    thwarted: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class WaterLiftRow(Base):
    __tablename__ = "water_lifts"
    __table_args__ = (at_least("count", 0), at_least("since_epoch", 0))

    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    device: Mapped[WaterLift] = mapped_column(enum_type(WaterLift, "device"), primary_key=True)
    count: Mapped[int] = mapped_column(default=1)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class NavigationKitRow(Base):
    __tablename__ = "navigation_kits"
    __table_args__ = (between("quality", PERCENT_MIN, PERCENT_MAX), at_least("since_epoch", 0))

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    aid: Mapped[NavigationAid] = mapped_column(enum_type(NavigationAid, "aid"), primary_key=True)
    quality: Mapped[int] = mapped_column(default=50)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ContainerStockRow(Base):
    __tablename__ = "container_stocks"
    __table_args__ = (at_least("count", 0), at_least("broken", 0), Index("ix_container_stocks_kind", "kind"))

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[ContainerKind] = mapped_column(enum_type(ContainerKind, "kind"), primary_key=True)
    count: Mapped[int] = mapped_column(default=0)
    broken: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
