from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.climes import CirculationBand, OscillationPhase
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

WIND_FIELDS = ("band", "summer_band", "wind_from", "strength", "windward", "shadow", "monsoon", "upwelling")
MONSOON_FIELDS = ("strength", "failed")
OSCILLATION_FIELDS = ("phase", "period", "step", "strength")
WINDOW_FIELDS = ("synodic", "offset", "open")
COSMOPOLITAN_FIELDS = ("name", "lingua_franca_entity_id", "strength")
COSMOPOLITAN_MEMBER_FIELDS = ("share",)
OCTANT_MAX = 7
SYNODIC_MAX = 100


class RegionWindRow(Base):
    __tablename__ = "region_winds"
    __table_args__ = (
        between("wind_from", 0, OCTANT_MAX),
        between("strength", PERCENT_MIN, PERCENT_MAX),
        between("shadow", PERCENT_MIN, PERCENT_MAX),
        between("monsoon", PERCENT_MIN, PERCENT_MAX),
        at_least("read_epoch", 0),
    )

    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    band: Mapped[CirculationBand] = mapped_column(enum_type(CirculationBand, "band"))
    summer_band: Mapped[CirculationBand] = mapped_column(enum_type(CirculationBand, "summer_band"), default=CirculationBand.TRADE)
    wind_from: Mapped[int] = mapped_column(default=0)
    strength: Mapped[int] = mapped_column(default=40)
    windward: Mapped[bool] = mapped_column(default=False)
    shadow: Mapped[int] = mapped_column(default=0)
    monsoon: Mapped[int] = mapped_column(default=0)
    upwelling: Mapped[bool] = mapped_column(default=False)
    read_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MonsoonSeasonRow(Base):
    __tablename__ = "monsoon_seasons"
    __table_args__ = (between("strength", 0, PERCENT_MAX * 2), at_least("epoch", 0))

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    epoch: Mapped[int] = mapped_column(primary_key=True)
    strength: Mapped[int] = mapped_column(default=100)
    failed: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ClimateOscillationRow(Base):
    __tablename__ = "climate_oscillations"
    __table_args__ = (between("period", 2, SYNODIC_MAX), at_least("step", 0), between("strength", PERCENT_MIN, PERCENT_MAX))

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    phase: Mapped[OscillationPhase] = mapped_column(enum_type(OscillationPhase, "phase"), default=OscillationPhase.NEUTRAL)
    period: Mapped[int] = mapped_column(default=6)
    step: Mapped[int] = mapped_column(default=0)
    strength: Mapped[int] = mapped_column(default=10)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LaunchWindowRow(Base):
    __tablename__ = "launch_windows"
    __table_args__ = (between("synodic", 1, SYNODIC_MAX), at_least("offset", 0))

    from_world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    to_world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    synodic: Mapped[int] = mapped_column(default=4)
    offset: Mapped[int] = mapped_column(default=0)
    open: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CosmopolitanCultureRow(Base):
    __tablename__ = "cosmopolitan_cultures"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX), at_least("formed_epoch", 0), Index("ix_cosmopolitan_cultures_route", "route_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    lingua_franca_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    strength: Mapped[int] = mapped_column(default=20)
    values: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    formed_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CosmopolitanMemberRow(Base):
    __tablename__ = "cosmopolitan_members"
    __table_args__ = (between("share", PERCENT_MIN, PERCENT_MAX), at_least("joined_epoch", 0))

    culture_id: Mapped[int] = mapped_column(ForeignKey("cosmopolitan_cultures.id", ondelete="CASCADE"), primary_key=True)
    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True, index=True)
    share: Mapped[int] = mapped_column(default=20)
    joined_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
