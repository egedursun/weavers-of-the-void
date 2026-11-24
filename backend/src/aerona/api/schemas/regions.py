from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.environment import RiverClass, TerrainKind
from aerona.domain.enums.geology import BuildingGrade, DeepPassageKind, DeepPassageOrigin, DeepPassageState, RockKind, UndergroundStratum
from aerona.domain.enums.region import DangerHarm, DangerOrigin, DangerSource, HazardSeason, MemoryOrigin, RegionMemoryKind, TerrainHazard


class RegionDangerView(ApiModel):
    id: int
    source: DangerSource
    label: str
    strength: int
    origin: DangerOrigin
    held: bool
    source_node_id: int | None
    source_node_name: str | None
    son_id: int | None
    since_epoch: int
    harms: dict[DangerHarm, int]
    targets: list[DangerHarm]
    reachable: list[DangerHarm]


class RegionMemoryView(ApiModel):
    id: int
    kind: RegionMemoryKind
    label: str
    magnitude: int
    epoch: int
    title: str
    origin: MemoryOrigin
    held: bool
    darkness: int
    holiness: int
    fades: bool
    subject_id: int | None
    incident_id: int | None


class MapKnowledgeView(ApiModel):
    polity_id: int
    polity_name: str
    level: int
    held: bool
    terrain: bool
    sacred: bool
    minerals: bool
    unmapped: bool


class RealmChoice(ApiModel):
    id: int
    name: str


class RegionHazardView(ApiModel):
    id: int
    hazard: TerrainHazard
    label: str
    epoch: int
    year: int | None
    season_name: str | None
    deaths: int
    injured: int
    soldiers_lost: int


class HazardExposure(ApiModel):
    hazard: TerrainHazard
    label: str
    season: HazardSeason


class RiverNeighbour(ApiModel):
    id: int
    name: str
    river_class: RiverClass | None


class RegionTerrainView(ApiModel):
    region_id: int
    world_id: int
    danger: int
    harms: dict[DangerHarm, int]
    dangers: list[RegionDangerView]
    sacredness: int
    sacredness_held: bool
    darkness: int
    holiness: int
    haunting_pct: int
    draws_pilgrims: bool
    pilgrim_sacred_min: int
    memories: list[RegionMemoryView]
    knowledge: list[MapKnowledgeView]
    realms: list[RealmChoice]
    unmapped_below: int
    hazards: list[RegionHazardView]
    exposure: list[HazardExposure]
    river_class: RiverClass
    river_neighbours: list[RiverNeighbour]


class RockLayerView(ApiModel):
    id: int
    depth_order: int
    rock: RockKind
    thickness: int
    top: int
    veins: dict[str, int]
    reached_epoch: int | None
    hardness: int
    porosity: int
    solubility: int
    workability: int
    grade: BuildingGrade
    locked: list[str]


class DepthStratumView(ApiModel):
    id: int
    stratum: UndergroundStratum
    depth: int
    volume: int
    pressure: int
    reached_epoch: int | None
    breached_epoch: int | None
    tapped_epoch: int | None
    name: str | None
    terrain: TerrainKind
    extent: int
    light: int
    realm: NodeRef | None
    holder: NodeRef | None
    dwellers: list[NodeRef]
    dwellable: bool
    locked: list[str]


class DeepPassageView(ApiModel):
    id: int
    kind: DeepPassageKind
    state: DeepPassageState
    origin: DeepPassageOrigin
    width: int
    progress: int
    near_stratum: UndergroundStratum | None
    far_region: NodeRef | None
    far_stratum: UndergroundStratum | None
    place: NodeRef | None
    digger: NodeRef | None
    locked: list[str]


class BeneathView(ApiModel):
    region_id: int
    mined_depth: int
    quarry_grade: BuildingGrade
    carvable: bool
    layers: list[RockLayerView]
    strata: list[DepthStratumView]
    passages: list[DeepPassageView]
