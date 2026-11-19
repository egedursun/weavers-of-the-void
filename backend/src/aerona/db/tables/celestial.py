from types import MappingProxyType
from typing import Any

from sqlalchemy import JSON, CheckConstraint, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base, TimestampMixin
from aerona.db.columns import at_least, between, enum_type
from aerona.db.tables.node import NodeRow
from aerona.db.types import PydanticJSON
from aerona.domain.enums.cosmography import GalacticZone, StarAge, WorldAge
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.world import Atmosphere, ClimateEra, Discovery, Gravity, SkyEventKind, StarType, WorldType
from aerona.domain.models.phonology import Phonology
from aerona.domain.models.profiles import EntityDepth

SEASONS_MAX = 12


class StarRow(NodeRow):
    __tablename__ = "stars"
    __table_args__ = (
        between("brightness", PERCENT_MIN, PERCENT_MAX),
        between("stability", PERCENT_MIN, PERCENT_MAX),
        between("radiation", PERCENT_MIN, PERCENT_MAX),
        between("sacredness", PERCENT_MIN, PERCENT_MAX),
        CheckConstraint("lifecycle_clock IS NULL OR lifecycle_clock >= 0", name="lifecycle_clock_min"),
    )
    __mapper_args__ = MappingProxyType({"polymorphic_identity": NodeKind.STAR, "polymorphic_load": "inline"})

    id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    star_type: Mapped[StarType] = mapped_column(enum_type(StarType, "star_type"))
    brightness: Mapped[int]
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(Text)
    image_prompt: Mapped[str | None] = mapped_column(Text)
    depth: Mapped[EntityDepth | None] = mapped_column(PydanticJSON(EntityDepth))
    created_epoch: Mapped[int]
    galaxy_id: Mapped[int | None] = mapped_column(ForeignKey("galaxies.id", ondelete="SET NULL"), index=True)
    structure_id: Mapped[int | None] = mapped_column(ForeignKey("galactic_structures.id", ondelete="SET NULL"), index=True)
    galactic_zone: Mapped[GalacticZone] = mapped_column(enum_type(GalacticZone, "galactic_zone"), default=GalacticZone.OUTER_DISC)
    age_stage: Mapped[StarAge] = mapped_column(enum_type(StarAge, "age_stage"), default=StarAge.MAIN)
    lifecycle_clock: Mapped[int | None]
    stability: Mapped[int] = mapped_column(default=70)
    radiation: Mapped[int] = mapped_column(default=20)
    sacredness: Mapped[int] = mapped_column(default=0)
    patron_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL", use_alter=True), index=True)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class WorldRow(NodeRow):
    __tablename__ = "worlds"
    __table_args__ = (
        between("danger", PERCENT_MIN, PERCENT_MAX),
        between("leakage", PERCENT_MIN, PERCENT_MAX),
        CheckConstraint("orbit > 0", name="orbit_positive"),
        CheckConstraint("time_factor > 0", name="time_factor_positive"),
        CheckConstraint("terrain_sea BETWEEN 0 AND 1", name="terrain_sea_range"),
        CheckConstraint("terrain_humidity BETWEEN -1 AND 1", name="terrain_humidity_range"),
        CheckConstraint("terrain_mountains >= 0", name="terrain_mountains_min"),
        CheckConstraint("parent_world_id IS NULL OR parent_world_id <> id", name="not_own_moon"),
        CheckConstraint("mirror_twin_id IS NULL OR mirror_twin_id <> id", name="not_own_twin"),
        CheckConstraint("mortal_agents IS NULL OR mortal_agents >= 0", name="mortal_agents_min"),
        CheckConstraint("climate_epochs_left IS NULL OR climate_epochs_left >= 0", name="climate_epochs_left_min"),
        CheckConstraint("axial_tilt IS NULL OR axial_tilt BETWEEN 0 AND 90", name="axial_tilt_range"),
        CheckConstraint(f"season_count IS NULL OR season_count BETWEEN 1 AND {SEASONS_MAX}", name="season_count_range"),
        CheckConstraint("year_length_days IS NULL OR year_length_days >= 1", name="year_length_positive"),
        CheckConstraint("day_length_hours IS NULL OR day_length_hours >= 1", name="day_length_positive"),
        CheckConstraint("moon_count IS NULL OR moon_count >= 0", name="moon_count_min"),
        CheckConstraint("tidal_strength IS NULL OR tidal_strength BETWEEN 0 AND 100", name="tidal_strength_range"),
        CheckConstraint("galaxy_id IS NULL OR dimension_id IS NULL", name="one_place"),
        CheckConstraint("(star_id IS NULL AND parent_world_id IS NULL) OR (galaxy_id IS NULL AND dimension_id IS NULL)", name="placed_by_star"),
        between("magnetism", PERCENT_MIN, PERCENT_MAX),
        between("radiation", PERCENT_MIN, PERCENT_MAX),
        between("biosphere_health", PERCENT_MIN, PERCENT_MAX),
        between("mood", -PERCENT_MAX, PERCENT_MAX),
        Index("ix_worlds_discovery", "discovery"),
    )
    __mapper_args__ = MappingProxyType({"polymorphic_identity": NodeKind.WORLD, "polymorphic_load": "inline"})

    id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    world_type: Mapped[WorldType] = mapped_column(enum_type(WorldType, "world_type"))
    star_id: Mapped[int | None] = mapped_column(ForeignKey("stars.id", ondelete="SET NULL"), index=True)
    parent_world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"), index=True)
    orbit: Mapped[float] = mapped_column(Float)
    gravity: Mapped[Gravity] = mapped_column(enum_type(Gravity, "gravity"), default=Gravity.NORMAL)
    atmosphere: Mapped[Atmosphere] = mapped_column(enum_type(Atmosphere, "atmosphere"), default=Atmosphere.NORMAL)
    time_factor: Mapped[float] = mapped_column(Float, default=1.0)
    terrain_seed: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    terrain_sea: Mapped[float] = mapped_column(Float)
    terrain_mountains: Mapped[float] = mapped_column(Float)
    terrain_humidity: Mapped[float] = mapped_column(Float)
    discovery: Mapped[Discovery] = mapped_column(enum_type(Discovery, "discovery"), default=Discovery.KNOWN)
    danger: Mapped[int]
    leakage: Mapped[int] = mapped_column(default=0)
    cosmology: Mapped[str | None] = mapped_column(Text)
    phonology: Mapped[Phonology | None] = mapped_column(PydanticJSON(Phonology))
    description: Mapped[str | None] = mapped_column(Text)
    image_prompt: Mapped[str | None] = mapped_column(Text)
    depth: Mapped[EntityDepth | None] = mapped_column(PydanticJSON(EntityDepth))
    creator_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL", use_alter=True), index=True)
    patron_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL", use_alter=True), index=True)
    patron_automatic: Mapped[bool] = mapped_column(default=False)
    epoch_star_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL", use_alter=True))
    mirror_twin_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    mortal_agents: Mapped[int | None]
    climate_era: Mapped[ClimateEra | None] = mapped_column(enum_type(ClimateEra, "climate_era"))
    climate_epochs_left: Mapped[int | None]
    climate_since_epoch: Mapped[int | None]
    climate_imposed_by_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL", use_alter=True))
    consciousness_closed: Mapped[bool] = mapped_column(default=False)
    created_epoch: Mapped[int]
    axial_tilt: Mapped[int | None]
    year_length_days: Mapped[int | None]
    season_count: Mapped[int | None]
    day_length_hours: Mapped[int | None]
    moon_count: Mapped[int | None]
    tidal_strength: Mapped[int | None]
    calendar_locked: Mapped[list[str]] = mapped_column(JSON, default=list)
    galaxy_id: Mapped[int | None] = mapped_column(ForeignKey("galaxies.id", ondelete="SET NULL"), index=True)
    dimension_id: Mapped[int | None] = mapped_column(ForeignKey("dimensions.id", ondelete="SET NULL"), index=True)
    magnetism: Mapped[int] = mapped_column(default=50)
    radiation: Mapped[int] = mapped_column(default=10)
    biosphere_health: Mapped[int] = mapped_column(default=80)
    age_stage: Mapped[WorldAge] = mapped_column(enum_type(WorldAge, "age_stage"), default=WorldAge.MATURE)
    mood: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class WorldMapRow(TimestampMixin, Base):
    __tablename__ = "world_maps"

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    generator_version: Mapped[int]
    epoch: Mapped[int]
    signature: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH), default="")
    geometry: Mapped[dict[str, Any]] = mapped_column(JSON)


class SkyEventRow(Base):
    __tablename__ = "sky_events"
    __table_args__ = (
        at_least("epoch", 1),
        CheckConstraint("until_epoch IS NULL OR until_epoch >= epoch", name="until_after_start"),
        Index("ix_sky_events_world_epoch", "world_id", "epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[SkyEventKind] = mapped_column(enum_type(SkyEventKind, "kind"))
    epoch: Mapped[int]
    until_epoch: Mapped[int | None]
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    star_id: Mapped[int | None] = mapped_column(ForeignKey("stars.id", ondelete="SET NULL"))
    route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id", ondelete="SET NULL"))
    caused_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    text: Mapped[str | None] = mapped_column(Text)
