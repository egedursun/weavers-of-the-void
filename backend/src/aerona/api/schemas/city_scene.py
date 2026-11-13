from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.environment import CoastKind, RiverClass, TemperatureBand, TerrainKind
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.settlement import DistrictKind, SizeTier, WaterSupply
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.structure import BuildingForm, ConstructionState, StructureGroup, StructureKind
from aerona.domain.enums.urban import CivicService, HousingLevel, LandCover, LandGround, Morphology, UrbanService, ZoneKind


class ServiceShare(ApiModel):
    service: UrbanService
    coverage: int


class CityDistrictView(ApiModel):
    id: int
    kind: DistrictKind
    zone: ZoneKind
    level: int
    housing: HousingLevel
    condition: int
    desirability: int
    land_value: int
    q: int
    r: int
    cells: list[list[int]]
    residents: int
    dwellings: int
    services: list[ServiceShare]
    turf: int
    locked: list[str]


class CityBuildingView(ApiModel):
    node: NodeRef
    kind: StructureKind
    zone: ZoneKind
    civic: CivicService | None
    service: UrbanService | None
    district_id: int | None
    home_district_id: int | None
    q: int
    r: int
    slot: int
    level: int
    condition: int
    state: ConstructionState
    progress: int
    staff_pct: int
    form: BuildingForm | None
    storeys: int | None


class ZoneShare(ApiModel):
    zone: ZoneKind
    districts: int
    cells: int
    buildings: int


class CitySceneView(ApiModel):
    town: NodeRef
    morphology: Morphology
    tier: SizeTier
    population: int
    homeless: int
    shelters: int
    walls_level: int
    walls_radius: int | None
    roads: int
    water: WaterSupply
    water_side: int | None
    scale: int
    districts: list[CityDistrictView]
    buildings: list[CityBuildingView]
    zones: list[ZoneShare]


class LandTileView(ApiModel):
    q: int
    r: int
    ground: LandGround
    cover: LandCover
    river: bool


class LandPlaceView(ApiModel):
    node: NodeRef
    q: int
    r: int
    detail: str
    kind: PlaceKind | None
    sacred: bool


class LandWorkView(ApiModel):
    node: NodeRef
    kind: StructureKind
    state: ConstructionState
    level: int
    condition: int
    progress: int
    q: int
    r: int
    form: BuildingForm | None
    storeys: int | None


class LandResourceView(ApiModel):
    node: NodeRef
    commodity: CommodityKind
    richness: int
    reserve: int
    initial_reserve: int
    q: int
    r: int


class LandSceneView(ApiModel):
    region: NodeRef
    terrain: TerrainKind
    elevation: int
    roughness: int
    moisture: int
    forest_cover: int
    farmed: int
    grazed: int
    wetland: int
    cleared: int
    mined: int
    built: int
    soil_fertility: int
    magic_density: int
    river: RiverClass
    coast: CoastKind
    temperature: TemperatureBand
    tiles: list[LandTileView]
    settlements: list[LandPlaceView]
    places: list[LandPlaceView]
    works: list[LandWorkView]
    resources: list[LandResourceView]


class TypeInstanceView(ApiModel):
    node: NodeRef
    town: NodeRef | None
    state: ConstructionState
    level: int


class StructureTypeView(ApiModel):
    kind: StructureKind
    label: str
    zone: ZoneKind
    group: StructureGroup | None
    civic: CivicService | None
    service: UrbanService | None
    amenity: bool
    nuisance: bool
    staff: SocialClass | None
    tier: SizeTier | None
    upkeep: CommodityKind | None
    instances: list[TypeInstanceView]


class DwellingTypeView(ApiModel):
    housing: HousingLevel
    districts: int
    dwellings: int
    towns: list[NodeRef]


class StructureTypesView(ApiModel):
    world_id: int
    structures: list[StructureTypeView]
    dwellings: list[DwellingTypeView]
