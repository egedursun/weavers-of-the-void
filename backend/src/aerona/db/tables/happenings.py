from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base, CreatedAtMixin
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.demography import AgeBand, Sex
from aerona.domain.enums.environment import RiverClass
from aerona.domain.enums.happening import EventPhase, RiverShiftCause
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.society import SocialClass


class EventProfileRow(Base):
    __tablename__ = "event_profiles"
    __table_args__ = (
        at_least("start_epoch", 0),
        at_least("phase_epoch", 0),
        CheckConstraint("end_epoch IS NULL OR end_epoch >= start_epoch", name="end_after_start"),
        CheckConstraint("end_year IS NULL OR start_year IS NULL OR end_year >= start_year", name="end_year_after_start"),
        Index("ix_event_profiles_world_phase", "world_id", "phase"),
    )

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    start_epoch: Mapped[int]
    start_year: Mapped[int | None]
    start_season: Mapped[int | None]
    end_epoch: Mapped[int | None]
    end_year: Mapped[int | None]
    end_season: Mapped[int | None]
    phase: Mapped[EventPhase] = mapped_column(enum_type(EventPhase, "phase"), default=EventPhase.ONSET)
    phase_epoch: Mapped[int]
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    siege_id: Mapped[int | None] = mapped_column(ForeignKey("sieges.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class EventFootprintRow(Base):
    __tablename__ = "event_footprints"
    __table_args__ = (at_least("joined_epoch", 0), Index("ix_event_footprints_region", "region_entity_id"))

    event_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    joined_epoch: Mapped[int]


class EventCasualtyRow(Base):
    __tablename__ = "event_casualties"
    __table_args__ = (at_least("count", 0), Index("ix_event_casualties_community", "community_entity_id"))

    event_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    age_band: Mapped[AgeBand] = mapped_column(enum_type(AgeBand, "age_band"), primary_key=True)
    sex: Mapped[Sex] = mapped_column(enum_type(Sex, "sex"), primary_key=True)
    social_class: Mapped[SocialClass] = mapped_column(enum_type(SocialClass, "social_class"), primary_key=True)
    phase: Mapped[EventPhase] = mapped_column(enum_type(EventPhase, "phase"), primary_key=True)
    count: Mapped[int] = mapped_column(default=0)


class RegionGeomorphRow(Base):
    __tablename__ = "region_geomorphology"
    __table_args__ = (
        between("desertification", PERCENT_MIN, PERCENT_MAX),
        between("volcanic_pressure", PERCENT_MIN, PERCENT_MAX),
        Index("ix_region_geomorphology_world", "world_id"),
    )

    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    desertification: Mapped[int] = mapped_column(default=0)
    desertified: Mapped[bool] = mapped_column(default=False)
    desert_since_epoch: Mapped[int | None]
    river_course: Mapped[RiverClass | None] = mapped_column(enum_type(RiverClass, "river_course"))
    course_changed_epoch: Mapped[int | None]
    volcanic: Mapped[bool] = mapped_column(default=False)
    volcanic_pressure: Mapped[int] = mapped_column(default=0)
    last_eruption_epoch: Mapped[int | None]
    ash_since_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class RiverShiftRow(CreatedAtMixin, Base):
    __tablename__ = "river_shifts"
    __table_args__ = (
        at_least("epoch", 1),
        CheckConstraint("from_region_id <> to_region_id", name="distinct_regions"),
        Index("ix_river_shifts_world_epoch", "world_id", "epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    from_region_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    to_region_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    epoch: Mapped[int]
    year: Mapped[int | None]
    river_class: Mapped[RiverClass] = mapped_column(enum_type(RiverClass, "river_class"))
    cause: Mapped[RiverShiftCause] = mapped_column(enum_type(RiverShiftCause, "cause"))
    event_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
