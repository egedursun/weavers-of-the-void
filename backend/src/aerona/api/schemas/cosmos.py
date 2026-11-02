from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import EntitySummary, ForeignGodRecord, JourneyRecord, NodeRef, RouteRecord, StarRecord, WorldRecord
from aerona.cartography.palette import WorldPalette
from aerona.domain.enums.chronicle import LegendaryQuestKind, LegendaryQuestOutcome, ThreadStatus
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.enums.travel import HorizonStatus, TravelMethod
from aerona.domain.enums.world import SkyEventKind, WorldType
from aerona.services.codex import Danger, GodLine, PeopleLine, ResourceLine, RouteLine


class WorldCounts(ApiModel):
    regions: int
    peoples: int
    settlements: int
    living: int
    population: int


class CosmosWorld(ApiModel):
    world: WorldRecord
    type_label: str
    counts: WorldCounts
    sons: list[NodeRef]
    cover: str | None


class WorldTypeLook(ApiModel):
    world_type: WorldType
    label: str
    palette: WorldPalette


class WorldLaw(ApiModel):
    entity: EntitySummary
    mechanic: NaturalLaw | None


class AddictionView(ApiModel):
    community: NodeRef
    resource: NodeRef
    owned_epochs: int
    addicted_since_epoch: int | None
    withdrawal_since_epoch: int | None


class SkyEventRecord(ApiModel):
    id: int
    kind: SkyEventKind
    epoch: int
    until_epoch: int | None
    world_id: int | None
    star_id: int | None
    route_id: int | None
    text: str | None


class CosmosView(ApiModel):
    stars: list[StarRecord]
    worlds: list[CosmosWorld]
    foreign_gods: list[ForeignGodRecord]
    routes: list[RouteRecord]
    journeys: list[JourneyRecord]
    sky_events: list[SkyEventRecord]
    world_types: list[WorldTypeLook]
    places: list[EntitySummary]
    communities: list[EntitySummary]


class SensedWorld(ApiModel):
    id: int
    mortal_entity_id: int
    world_id: int | None
    epoch: int
    how: str | None
    method: TravelMethod | None
    status: HorizonStatus
    result_world_id: int | None


class DiscoveryWorld(ApiModel):
    world_id: int
    name: str
    discovery: str
    regions: int
    places: int
    communities: int


class DiscoverySummary(ApiModel):
    worlds: list[DiscoveryWorld]
    sensed: list[SensedWorld]


class TravellerGuideView(ApiModel):
    world: WorldRecord
    type_label: str
    star: str | None
    star_type: str | None
    parent: str | None
    atmosphere: str
    gravity: str
    discovery: str
    climate: str | None
    climate_epochs_left: int | None
    dangers: list[Danger]
    peoples: list[PeopleLine]
    resources: list[ResourceLine]
    routes: list[RouteLine]
    foreign_gods: list[GodLine]
    sky: list[EntitySummary]


class EpochStarWorld(ApiModel):
    world_id: int
    world_name: str
    star: EntitySummary | None


class EpochStarEntry(ApiModel):
    epoch: int
    entity_id: int | None
    name: str | None
    text: str


class EpochStarView(ApiModel):
    current: list[EpochStarWorld]
    history: list[EpochStarEntry]


class GreatExpedition(ApiModel):
    thread_id: int
    kind: LegendaryQuestKind
    name: str
    text: str
    declared_by: ActorKind
    opened_epoch: int
    deadline_epoch: int
    epochs_remaining: int
    thread_status: ThreadStatus
    outcome: LegendaryQuestOutcome | None
    target_star_id: int | None
    target_route_id: int | None
    target_entity_id: int | None


class WorldPulseView(ApiModel):
    world_id: int
    communities: int
    godless: int
    factions: int
    cults: int
    named_mortals: int
    sons: int
    son_share: int | None
    engine_records: int
    this_epoch: int
    per_epoch: int
    quota: int
    window: int
