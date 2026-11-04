from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.environment import (
    CoastKind,
    NotableYearKind,
    PlaceCover,
    RiverClass,
    SoilKind,
    TemperatureBand,
    TerrainKind,
    WaterSource,
    WeatherEffect,
    WeatherKind,
)
from aerona.domain.enums.world import ClimateEra


class WeatherForecast(ApiModel):
    season_id: int | None
    season_name: str | None
    kind: WeatherKind
    label: str
    effects: dict[WeatherEffect, int]


class LeyLineView(ApiModel):
    id: int
    other_region_id: int
    other_region_name: str
    strength: int
    severed: bool
    severed_until_epoch: int | None
    forged: bool


class NotableYearView(ApiModel):
    id: int
    epoch: int
    year: int
    kind: NotableYearKind
    weather: WeatherKind | None
    name: str
    magnitude: int
    region_id: int | None
    legend_id: int | None = None


class ForcedWeatherView(ApiModel):
    id: int
    kind: WeatherKind
    label: str
    from_epoch: int
    until_epoch: int
    season_position: int | None
    son_id: int | None


class NeighbourRegion(ApiModel):
    id: int
    name: str


class RegionEnvironmentView(ApiModel):
    region_id: int
    world_id: int
    surveyed: bool
    biome_mix: list[int]
    dominant_terrain: TerrainKind
    elevation_mean: int
    roughness: int
    latitude: int
    moisture: int
    base_forest: int
    forest_cover: int
    base_wetland: int
    wetland: int
    river_class: RiverClass
    coast_kind: CoastKind
    soil: SoilKind
    soil_fertility: int
    soil_base: int
    fertility: int | None
    temperature: int
    temperature_band: TemperatureBand
    rainfall: int
    seasonality: int
    disease_load: int
    magic_density: int
    defensibility: int
    passability: dict[str, int]
    mineral_layers: dict[str, int]
    scars: dict[str, int]
    land_use: dict[str, int]
    erosion: int
    harvest_pct: int
    locked: list[str]
    forecast: list[WeatherForecast]
    ley_lines: list[LeyLineView]
    forced_weather: list[ForcedWeatherView]
    neighbours: list[NeighbourRegion]
    notable_years: list[NotableYearView]


class PlaceEnvironmentView(ApiModel):
    place_id: int
    region_id: int | None
    terrain: TerrainKind | None
    cover: PlaceCover
    water_source: WaterSource
    height_advantage: int
    chokepoint: bool
    nexus: bool
    soil_fertility: int
    locked: list[str]


class SeasonView(ApiModel):
    id: int
    position: int
    name: str
    temperature_shift: int
    rain_shift: int
    growth: int
    travel: int
    campaign: int
    edited: bool


class HolyDayView(ApiModel):
    name: str
    year: int | None


class CalendarView(ApiModel):
    knowledge_id: int
    name: str
    adopted_epoch: int
    anchor_year: int
    month_names: list[str]
    holy_days: list[HolyDayView]


class ClimateAgeView(ApiModel):
    era: ClimateEra
    label: str
    description: str
    since_epoch: int | None
    epochs_left: int | None
    imposed: bool


class AstronomyRecordView(ApiModel):
    id: int
    name: str


class WorldSeasonsView(ApiModel):
    world_id: int
    climate: ClimateAgeView | None
    axial_tilt: int | None
    year_length_days: int | None
    season_count: int | None
    day_length_hours: int | None
    moon_count: int | None
    tidal_strength: int | None
    seasons: list[SeasonView]
    calendars: list[CalendarView]
    notable_years: list[NotableYearView]
    astronomy_records: list[AstronomyRecordView]
