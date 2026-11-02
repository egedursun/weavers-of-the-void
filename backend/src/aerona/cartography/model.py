from enum import IntEnum, StrEnum

from pydantic import BaseModel, ConfigDict, Field

from aerona.cartography.biomes import Biome
from aerona.cartography.palette import WorldPalette
from aerona.cartography.terrain import TerrainOverrides
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass
from aerona.domain.enums.world import WorldType

Coordinates = tuple[float, float]


class PlacementPreference(StrEnum):
    COASTAL_LOWLAND = "coastal_lowland"
    HIGHLAND = "highland"
    ANYWHERE = "anywhere"


MARKER_TYPES = frozenset(
    {
        EntityType.PLACE,
        EntityType.RESOURCE,
        EntityType.SETTLEMENT,
        EntityType.PEOPLE,
        EntityType.CULT,
        EntityType.FACTION,
        EntityType.MORTAL,
        EntityType.ITEM,
        EntityType.EVENT,
        EntityType.SPECIES,
    }
)

PLACEMENT_PREFERENCES: dict[EntityType, PlacementPreference] = {
    EntityType.SETTLEMENT: PlacementPreference.COASTAL_LOWLAND,
    EntityType.RESOURCE: PlacementPreference.HIGHLAND,
}


def placement_preference(entity_type: EntityType) -> PlacementPreference:
    return PLACEMENT_PREFERENCES.get(entity_type, PlacementPreference.ANYWHERE)


class RegionInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int = Field(ge=0)
    parent_id: int | None = None
    is_water: bool = False
    position: Coordinates | None = None


class MarkerInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int = Field(ge=0)
    parent_id: int | None = None
    position: Coordinates | None = None
    preference: PlacementPreference = PlacementPreference.ANYWHERE


class MapRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    seed: str
    world_type: WorldType = WorldType.ORDINARY
    terrain: TerrainOverrides = TerrainOverrides()
    regions: tuple[RegionInput, ...] = ()
    markers: tuple[MarkerInput, ...] = ()


class ElevationClass(StrEnum):
    MOUNTAINOUS = "mountainous"
    HILLY = "hilly"
    PLAIN = "plain"
    WATER = "water"


class BorderKind(StrEnum):
    COAST = "coast"
    REGION = "region"
    SUB_REGION = "sub_region"


class KnownState(IntEnum):
    UNKNOWN = 0
    KNOWN = 1
    FOG = 2


class MapWindow(BaseModel):
    x: float
    y: float
    width: float
    height: float


class KnownExtent(BaseModel):
    x: float
    y: float
    width: float
    height: float
    known_ratio: float
    known_cells: int


class ClimateShare(BaseModel):
    biome: Biome
    name: str
    share_pct: int


class RegionGeography(BaseModel):
    biome_mix: list[int]
    elevation_mean: int
    roughness: int
    moisture: int
    latitude: int
    forest: int
    wetland: int
    river_flow: float
    river_class: RiverClass
    coast_kind: CoastKind
    land_share: int


class RegionRecord(BaseModel):
    id: int
    parent_id: int | None
    top_level_id: int
    depth: int
    is_water: bool
    seed: Coordinates | None
    anchor: Coordinates | None
    centroid: Coordinates | None
    size: int
    coastal: bool
    mean_elevation: float
    elevation_class: ElevationClass
    climate: list[ClimateShare]
    neighbours: list[int]
    bordering: list[int]
    geography: RegionGeography | None = None


class PlacedMarker(BaseModel):
    id: int
    x: float
    y: float
    cell: int
    region_id: int | None


class PositionUpdate(BaseModel):
    id: int
    x: int
    y: int


class CellLayer(BaseModel):
    x: list[float]
    y: list[float]
    elevation: list[float]
    moisture: list[float]
    shade: list[float]
    water: list[bool]
    coastal: list[bool]
    biome: list[int]
    region: list[int | None]
    top_region: list[int | None]
    known: list[int]
    polygon_offsets: list[int]
    polygon_coordinates: list[float]


class BorderLayer(BaseModel):
    kinds: list[BorderKind]
    coordinates: list[float]


class WorldMap(BaseModel):
    seed: str
    world_type: WorldType
    window: MapWindow
    extent: KnownExtent
    palette: WorldPalette
    cells: CellLayer
    borders: BorderLayer
    regions: list[RegionRecord]
    markers: list[PlacedMarker]
    new_positions: list[PositionUpdate]
    relocated_positions: list[PositionUpdate]
