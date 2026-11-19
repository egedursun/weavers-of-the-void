from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.space_weather import SpaceWeatherKind


class WorldFieldRow(Base):
    __tablename__ = "world_fields"
    __table_args__ = (
        between("shielding", 0, 100),
        between("surface_dose", 0, 100),
        between("compass_error", 0, 100),
        between("aurora_reach", 0, 100),
        at_least("reversal_left", 0),
        between("shift", -100, 100),
        at_least("shift_left", 0),
    )

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    shielding: Mapped[int] = mapped_column(default=50)
    surface_dose: Mapped[int] = mapped_column(default=0)
    compass_error: Mapped[int] = mapped_column(default=0)
    aurora_reach: Mapped[int] = mapped_column(default=10)
    reversal_epoch: Mapped[int | None]
    reversal_left: Mapped[int] = mapped_column(default=0)
    shift: Mapped[int] = mapped_column(default=0)
    shift_left: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class StarActivityRow(Base):
    __tablename__ = "star_activity"
    __table_args__ = (
        at_least("cycle_years", 1),
        between("phase", 0, 99),
        between("flare_rate", 0, 100),
        between("storm_rate", 0, 100),
        between("wind", 0, 100),
    )

    star_id: Mapped[int] = mapped_column(ForeignKey("stars.id", ondelete="CASCADE"), primary_key=True)
    cycle_years: Mapped[int] = mapped_column(default=11)
    phase: Mapped[int] = mapped_column(default=0)
    flare_rate: Mapped[int] = mapped_column(default=30)
    storm_rate: Mapped[int] = mapped_column(default=20)
    wind: Mapped[int] = mapped_column(default=40)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SpaceWeatherEventRow(Base):
    __tablename__ = "space_weather_events"
    __table_args__ = (between("strength", 0, 100), between("dose", 0, 100), at_least("epoch", 0), Index("ix_space_weather_events_world", "world_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    star_id: Mapped[int | None] = mapped_column(ForeignKey("stars.id", ondelete="SET NULL"), index=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    kind: Mapped[SpaceWeatherKind] = mapped_column(enum_type(SpaceWeatherKind, "kind"))
    strength: Mapped[int] = mapped_column(default=30)
    dose: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
