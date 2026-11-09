from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base, CreatedAtMixin
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.cosmography import OceanCurrent
from aerona.domain.enums.environment import (
    CoastKind,
    NotableYearKind,
    PlaceCover,
    RiverClass,
    SoilKind,
    TemperatureBand,
    TerrainKind,
    WaterSource,
    WeatherKind,
)
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

PERCENT_COLUMNS = (
    "elevation_mean",
    "roughness",
    "latitude",
    "moisture",
    "base_forest",
    "forest_cover",
    "base_wetland",
    "wetland",
    "soil_fertility",
    "soil_base",
    "temperature",
    "rainfall",
    "seasonality",
    "disease_load",
    "magic_density",
    "defensibility",
    "cleared",
    "farmed",
    "grazed",
    "mined",
    "built",
    "erosion",
    "sacredness",
    "leak",
)


class RegionEnvironmentRow(Base):
    __tablename__ = "region_environment"
    __table_args__ = (
        *(between(column, PERCENT_MIN, PERCENT_MAX) for column in PERCENT_COLUMNS),
        at_least("harvest_pct", 0),
        between("temperature_shift", -PERCENT_MAX, PERCENT_MAX),
        between("rainfall_shift", -PERCENT_MAX, PERCENT_MAX),
        Index("ix_region_environment_world", "world_id"),
    )

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    surveyed: Mapped[bool] = mapped_column(default=False)
    biome_mix: Mapped[list[int]] = mapped_column(JSON, default=list)
    dominant_terrain: Mapped[TerrainKind] = mapped_column(enum_type(TerrainKind, "dominant_terrain"))
    elevation_mean: Mapped[int]
    roughness: Mapped[int]
    latitude: Mapped[int]
    moisture: Mapped[int]
    base_forest: Mapped[int]
    forest_cover: Mapped[int]
    base_wetland: Mapped[int]
    wetland: Mapped[int]
    river_class: Mapped[RiverClass] = mapped_column(enum_type(RiverClass, "river_class"))
    coast_kind: Mapped[CoastKind] = mapped_column(enum_type(CoastKind, "coast_kind"))
    soil: Mapped[SoilKind] = mapped_column(enum_type(SoilKind, "soil"))
    soil_fertility: Mapped[int]
    soil_base: Mapped[int]
    temperature: Mapped[int]
    temperature_band: Mapped[TemperatureBand] = mapped_column(enum_type(TemperatureBand, "temperature_band"))
    rainfall: Mapped[int]
    seasonality: Mapped[int]
    disease_load: Mapped[int]
    mineral_layers: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    magic_density: Mapped[int]
    passability: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    defensibility: Mapped[int]
    scars: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    cleared: Mapped[int] = mapped_column(default=0)
    farmed: Mapped[int] = mapped_column(default=0)
    grazed: Mapped[int] = mapped_column(default=0)
    mined: Mapped[int] = mapped_column(default=0)
    built: Mapped[int] = mapped_column(default=0)
    erosion: Mapped[int] = mapped_column(default=0)
    harvest_pct: Mapped[int] = mapped_column(default=100)
    derived_fertility: Mapped[int | None]
    sacredness: Mapped[int] = mapped_column(default=0)
    leak: Mapped[int] = mapped_column(default=0)
    current: Mapped[OceanCurrent] = mapped_column(enum_type(OceanCurrent, "current"), default=OceanCurrent.NONE)
    temperature_shift: Mapped[int] = mapped_column(default=0)
    rainfall_shift: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PlaceEnvironmentRow(Base):
    __tablename__ = "place_environment"
    __table_args__ = (
        between("height_advantage", PERCENT_MIN, PERCENT_MAX),
        between("soil_fertility", PERCENT_MIN, PERCENT_MAX),
    )

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    region_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    terrain: Mapped[TerrainKind | None] = mapped_column(enum_type(TerrainKind, "terrain"))
    cover: Mapped[PlaceCover] = mapped_column(enum_type(PlaceCover, "cover"))
    water_source: Mapped[WaterSource] = mapped_column(enum_type(WaterSource, "water_source"))
    height_advantage: Mapped[int]
    chokepoint: Mapped[bool] = mapped_column(default=False)
    nexus: Mapped[bool] = mapped_column(default=False)
    soil_fertility: Mapped[int]
    derived_fertility: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class WorldSeasonRow(Base):
    __tablename__ = "world_seasons"
    __table_args__ = (
        at_least("position", 0),
        between("growth", PERCENT_MIN, PERCENT_MAX),
        between("travel", PERCENT_MIN, PERCENT_MAX),
        between("campaign", PERCENT_MIN, PERCENT_MAX),
        UniqueConstraint("world_id", "position", name="one_season_per_position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), index=True)
    position: Mapped[int]
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    temperature_shift: Mapped[int]
    rain_shift: Mapped[int]
    growth: Mapped[int]
    travel: Mapped[int]
    campaign: Mapped[int]
    edited: Mapped[bool] = mapped_column(default=False)


class NotableYearRow(CreatedAtMixin, Base):
    __tablename__ = "notable_years"
    __table_args__ = (
        at_least("epoch", 1),
        at_least("year", 0),
        at_least("magnitude", 0),
        Index("ix_notable_years_world_year", "world_id", "year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    region_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    epoch: Mapped[int]
    year: Mapped[int]
    kind: Mapped[NotableYearKind] = mapped_column(enum_type(NotableYearKind, "kind"))
    weather: Mapped[WeatherKind | None] = mapped_column(enum_type(WeatherKind, "weather"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    magnitude: Mapped[int]
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    legend_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))


class CalendarRow(CreatedAtMixin, Base):
    __tablename__ = "calendars"
    __table_args__ = (at_least("adopted_epoch", 0), at_least("anchor_year", 0))

    knowledge_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), index=True)
    adopted_epoch: Mapped[int]
    anchor_year: Mapped[int]
    anchor_incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    month_names: Mapped[list[str]] = mapped_column(JSON, default=list)
    holy_days: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


class LeyLineRow(Base):
    __tablename__ = "ley_lines"
    __table_args__ = (
        between("strength", PERCENT_MIN, PERCENT_MAX),
        CheckConstraint("region_a_id < region_b_id", name="ordered_pair"),
        UniqueConstraint("region_a_id", "region_b_id", name="one_line_per_pair"),
        Index("ix_ley_lines_world", "world_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    region_a_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    region_b_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    strength: Mapped[int]
    formed_epoch: Mapped[int]
    severed: Mapped[bool] = mapped_column(default=False)
    severed_until_epoch: Mapped[int | None]
    severed_by_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    forged: Mapped[bool] = mapped_column(default=False)


class StructureLeyRow(Base):
    __tablename__ = "structure_ley"

    structure_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    attuned: Mapped[bool] = mapped_column(default=False)
    on_ley_line: Mapped[bool] = mapped_column(default=False)
    at_nexus: Mapped[bool] = mapped_column(default=False)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ForcedWeatherRow(CreatedAtMixin, Base):
    __tablename__ = "forced_weather"
    __table_args__ = (
        at_least("from_epoch", 1),
        CheckConstraint("until_epoch >= from_epoch", name="ordered_epochs"),
        Index("ix_forced_weather_region", "region_entity_id", "until_epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    from_epoch: Mapped[int]
    until_epoch: Mapped[int]
    season_position: Mapped[int | None]
    kind: Mapped[WeatherKind] = mapped_column(enum_type(WeatherKind, "kind"))
    son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
