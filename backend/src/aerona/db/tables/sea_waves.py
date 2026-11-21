from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.forecasting import ObservationMethod
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.sea_waves import WaveOrigin


class SeaWaveRow(Base):
    __tablename__ = "sea_waves"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX), at_least("epoch", 0))

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), index=True)
    origin: Mapped[WaveOrigin] = mapped_column(enum_type(WaveOrigin, "origin"))
    origin_region_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    sea_region_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    strength: Mapped[int] = mapped_column(default=50)
    cause_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SeaWaveCoastRow(Base):
    __tablename__ = "sea_wave_coasts"
    __table_args__ = (
        between("height", PERCENT_MIN, PERCENT_MAX),
        at_least("delay", 0),
        at_least("dead", 0),
        Index("ix_sea_wave_coasts_region", "region_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    wave_id: Mapped[int] = mapped_column(ForeignKey("sea_waves.id", ondelete="CASCADE"), index=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    height: Mapped[int] = mapped_column(default=0)
    delay: Mapped[int] = mapped_column(default=0)
    warned: Mapped[bool] = mapped_column(default=False)
    dead: Mapped[int] = mapped_column(default=0)
    salted: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class WaveWarningRow(Base):
    __tablename__ = "wave_warnings"
    __table_args__ = (at_least("epoch", 0), at_least("until_epoch", 0), Index("ix_wave_warnings_region", "region_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    method: Mapped[ObservationMethod] = mapped_column(enum_type(ObservationMethod, "method"))
    by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    epoch: Mapped[int] = mapped_column(default=0)
    until_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
