from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import between, enum_type
from aerona.domain.enums.water import CoastForm, LocalClimateCause, SedimentCarrier, SedimentKind

MONTHS = 12


class RegionCryosphereRow(Base):
    __tablename__ = "region_cryosphere"
    __table_args__ = (
        between("ice_months", 0, MONTHS),
        between("ice_thickness", 0, 100),
        between("frozen_depth", 0, 100),
        between("thaw_months", 0, MONTHS),
        between("snowpack", 0, 100),
        between("melt_month", 0, MONTHS - 1),
        between("glacier_extent", 0, 100),
        between("glacier_trend", -100, 100),
        between("ice_shift", -MONTHS, MONTHS),
    )

    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    ice_months: Mapped[int] = mapped_column(default=0)
    ice_thickness: Mapped[int] = mapped_column(default=0)
    frozen_depth: Mapped[int] = mapped_column(default=0)
    thaw_months: Mapped[int] = mapped_column(default=0)
    snowpack: Mapped[int] = mapped_column(default=0)
    melt_month: Mapped[int] = mapped_column(default=3)
    glacier_extent: Mapped[int] = mapped_column(default=0)
    glacier_trend: Mapped[int] = mapped_column(default=0)
    ice_shift: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SedimentFlowRow(Base):
    __tablename__ = "sediment_flows"
    __table_args__ = (between("load", 0, 100), Index("ix_sediment_flows_sink", "sink_region_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    source_region_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    sink_region_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    carrier: Mapped[SedimentCarrier] = mapped_column(enum_type(SedimentCarrier, "carrier"))
    kind: Mapped[SedimentKind] = mapped_column(enum_type(SedimentKind, "kind"))
    load: Mapped[int] = mapped_column(default=20)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CoastRow(Base):
    __tablename__ = "coasts"
    __table_args__ = (between("rate", -100, 100), between("progress", -100, 100), between("harbour_silting", 0, 100))

    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    form: Mapped[CoastForm] = mapped_column(enum_type(CoastForm, "form"))
    rate: Mapped[int] = mapped_column(default=0)
    progress: Mapped[int] = mapped_column(default=0)
    harbour_silting: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LocalClimateRow(Base):
    __tablename__ = "local_climates"
    __table_args__ = (between("heat_shift", -50, 50), between("humidity_shift", -50, 50), between("wind_shift", -50, 50))

    place_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    cause: Mapped[LocalClimateCause] = mapped_column(enum_type(LocalClimateCause, "cause"))
    heat_shift: Mapped[int] = mapped_column(default=0)
    humidity_shift: Mapped[int] = mapped_column(default=0)
    wind_shift: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
