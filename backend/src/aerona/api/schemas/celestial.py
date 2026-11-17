from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.cosmos import SkyEventRecord, WorldCounts
from aerona.api.schemas.records import ChronicleLineRecord, EntitySummary, ForeignGodRecord, ImageRecord, NodeRef, RouteRecord, StarRecord, WorldRecord
from aerona.domain.models.profiles import EntityDepth


class PeopleBrief(ApiModel):
    entity: EntitySummary
    population: int
    cover: str | None


class WorldWiki(ApiModel):
    world: WorldRecord
    type_label: str
    cover: str | None
    depth: EntityDepth | None
    star: StarRecord | None
    counts: WorldCounts
    sons: list[NodeRef]
    patron: NodeRef | None
    foreign_gods: list[ForeignGodRecord]
    routes: list[RouteRecord]
    peoples: list[PeopleBrief]
    sky_events: list[SkyEventRecord]
    timeline: list[ChronicleLineRecord]
    timeline_total: int
    images: list[ImageRecord]


class OrbitingWorld(ApiModel):
    world: WorldRecord
    type_label: str
    cover: str | None
    population: int


class StarWiki(ApiModel):
    star: StarRecord
    type_label: str
    cover: str | None
    depth: EntityDepth | None
    worlds: list[OrbitingWorld]
    sky_events: list[SkyEventRecord]
    timeline: list[ChronicleLineRecord]
    timeline_total: int
    images: list[ImageRecord]
