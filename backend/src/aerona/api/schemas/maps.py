from enum import StrEnum

from pydantic import Field

from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import EntitySummary, MapNoteRecord, WorldRecord
from aerona.cartography.model import WorldMap
from aerona.domain.enums.culture import ArtMedium
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.ecology import BeastTemper
from aerona.domain.enums.economy import TradeMode, TradeRouteStatus
from aerona.domain.enums.faith import HoldingKind
from aerona.domain.enums.military import Stance
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.urban import ConvoyStatus
from aerona.domain.models.records import RegionControl
from aerona.services.wiki import EventMarker, RegionDominance, RoadKind, SettlementInfo


class RelationLineKind(StrEnum):
    TRADE = "trade"
    HOSTILITY = "hostility"
    RULE = "rule"
    HUNT = "hunt"


class GeographyPreview(ApiModel):
    world_id: int
    text: str


class MapPoint(ApiModel):
    entity: EntitySummary
    x: float | None
    y: float | None
    cover: str | None


class MapTime(ApiModel):
    current: int
    shown: int
    snapshots: list[int]


class MapRoad(ApiModel):
    first: int
    second: int
    kind: RoadKind
    length: float
    path: list[float]


class MapRelation(ApiModel):
    source: int
    target: int
    kind: RelationLineKind
    description: str | None
    path: list[float]


class MapWar(ApiModel):
    id: int
    war_id: int
    name: str
    location_id: int | None
    started_epoch: int
    ended_epoch: int | None
    ongoing: bool


class RegionGround(ApiModel):
    terrain: str
    soil: str
    climate: str
    land_use: str
    ley_lines: int
    nexus: bool
    rainfall: int = 0
    danger: int = 0
    danger_source: str | None = None
    sacredness: int = 0
    scar: str | None = None
    scar_depth: int = 0


class RegionStocks(ApiModel):
    population: int
    followers: int
    soldiers: int
    wildlife: int = 0
    desirability: int = 0
    coverage: int = 0
    niches: int = 0
    ring: int = 0
    market: int = 0
    soil: int = 0
    salt: int = 0
    solidarity: int = 0
    frontier: int = 0


class MapConvoy(ApiModel):
    convoy_id: int
    route_id: int
    owner: str
    status: ConvoyStatus
    guards: int
    path: list[float]


class MapTrade(ApiModel):
    route_id: int
    name: str
    first: int
    second: int
    mode: TradeMode
    status: TradeRouteStatus
    volume: int
    capacity: int
    path: list[float]


class RegionRealm(ApiModel):
    polity_id: int
    name: str
    control: int


class RegionDivineRule(ApiModel):
    god_id: int
    kind: NodeKind
    name: str
    share: int
    rivals: int


class RegionDeJure(ApiModel):
    title_id: int
    name: str
    polity_id: int | None
    held_by_right: bool


class MapLore(ApiModel):
    kind: str
    entity_id: int
    name: str
    place_id: int
    x: float
    y: float
    detail: str | None = None
    medium: ArtMedium | None = None


class MapLair(ApiModel):
    beast_id: int
    name: str
    x: float
    y: float
    terror: int
    temper: BeastTemper
    reach: int


class RegionTongue(ApiModel):
    language_id: int
    name: str
    prestige: int
    lingua_franca: bool


class MapArmy(ApiModel):
    army_id: int
    name: str
    owner_id: int
    war_id: int | None
    region_id: int | None
    stance: Stance
    size: int
    blockade_id: int | None
    path: list[float]


class MapOccupation(ApiModel):
    occupier_id: int
    name: str
    control: int
    resistance: int


class MapFront(ApiModel):
    war_id: int
    first_region_id: int
    second_region_id: int
    path: list[float]


class MapHoly(ApiModel):
    cult_id: int
    cult: str
    holding_id: int
    kind: HoldingKind
    x: float
    y: float


class MapOutbreak(ApiModel):
    outbreak_id: int
    disease_id: int
    disease: str
    region_id: int
    source_region_id: int | None
    status: OutbreakStatus
    severity: int
    dead: int
    endemic: bool
    path: list[float]


class MapView(ApiModel):
    world: WorldRecord
    geometry: WorldMap
    points: list[MapPoint]
    political: dict[int, RegionControl]
    roads: list[MapRoad]
    relations: list[MapRelation]
    wars: list[MapWar]
    settlements: dict[int, SettlementInfo]
    markers: list[EventMarker]
    dominance: dict[int, RegionDominance]
    region_creators: dict[int, int | None]
    population: dict[int, int]
    ground: dict[int, RegionGround]
    stocks: dict[int, RegionStocks]
    trade: list[MapTrade]
    convoys: list[MapConvoy] = Field(default_factory=list)
    outbreaks: list[MapOutbreak] = Field(default_factory=list)
    realms: dict[int, RegionRealm] = Field(default_factory=dict)
    de_jure: dict[int, RegionDeJure] = Field(default_factory=dict)
    dominion: dict[int, RegionDivineRule] = Field(default_factory=dict)
    armies: list[MapArmy] = Field(default_factory=list)
    occupations: dict[int, MapOccupation] = Field(default_factory=dict)
    fronts: list[MapFront] = Field(default_factory=list)
    holy: list[MapHoly] = Field(default_factory=list)
    lore: list[MapLore] = Field(default_factory=list)
    tongues: dict[int, RegionTongue] = Field(default_factory=dict)
    lairs: list[MapLair] = Field(default_factory=list)
    notes: list[MapNoteRecord]
    time: MapTime
