from enum import StrEnum

from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import EntitySummary, MapNoteRecord, WorldRecord
from aerona.cartography.model import WorldMap
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


class RegionStocks(ApiModel):
    population: int
    followers: int
    soldiers: int


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
    notes: list[MapNoteRecord]
    time: MapTime
