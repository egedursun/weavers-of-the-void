from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.gathering import (
    AttendanceReason,
    CollectionKind,
    CollectionRole,
    GatheringKind,
    GatheringOutcome,
    GatheringStatus,
    GuestRole,
    Milestone,
)
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.site import (
    BattlefieldFeature,
    ExcavationFind,
    ExcavationRisk,
    ExcavationStage,
    ExcavationStatus,
    RoomContentKind,
    SiteChallenge,
    SiteRoomKind,
)
from aerona.domain.enums.storyteller import SpontaneousKind, StorytellerProfile, TensionBand


class GuestView(ApiModel):
    node: NodeRef | None
    role: GuestRole
    reason: AttendanceReason
    invited: bool
    attended: bool | None
    harmed: bool
    locked: bool


class SeasonOption(ApiModel):
    position: int
    name: str


class GatheringView(ApiModel):
    id: int
    kind: GatheringKind
    status: GatheringStatus
    outcome: GatheringOutcome | None
    milestone: Milestone | None
    host: NodeRef | None
    place: NodeRef | None
    honoured: NodeRef | None
    tradition: NodeRef | None
    collection_id: int | None
    collection_name: str | None
    epoch: int
    year: int | None
    season: int | None
    season_name: str | None
    seasons: list[SeasonOption]
    cost: int
    food: int
    prestige: int
    by_player: bool
    note: str | None
    locked: list[str]
    guests: list[GuestView]


class NodeGatheringsView(ApiModel):
    node_id: int
    hosted: list[GatheringView]
    attended: list[GatheringView]


class CollectionView(ApiModel):
    id: int
    kind: CollectionKind
    name: str
    world_id: int | None
    start_epoch: int
    end_epoch: int | None
    parent_id: int | None
    note: str | None
    locked: list[str]
    members: int
    places: int


class LifeLogEntry(ApiModel):
    collection: CollectionView
    role: CollectionRole


class LifeLogView(ApiModel):
    node_id: int
    entries: list[LifeLogEntry]


class HistoryMemberView(ApiModel):
    node: NodeRef | None
    role: CollectionRole
    since_epoch: int


class IncidentLine(ApiModel):
    id: int
    epoch: int
    text: str | None


class HistoryDetail(ApiModel):
    collection: CollectionView
    parent: CollectionView | None
    children: list[CollectionView]
    roster: list[HistoryMemberView]
    sites: list[NodeRef]
    incidents: list[IncidentLine]


class HistoryPage(ApiModel):
    items: list[CollectionView]
    total: int


class TensionPoint(ApiModel):
    epoch: int
    tension: int
    target: int
    boost_pct: int
    band: TensionBand


class StorytellerView(ApiModel):
    world_id: int
    profile: StorytellerProfile
    tension: int
    target: int
    band: TensionBand
    boost_pct: int
    cycle_offset: int
    spotlight: NodeRef | None
    recent_kinds: dict[SpontaneousKind, int]
    updated_epoch: int
    locked: list[str]
    curve: list[TensionPoint]


class ContentView(ApiModel):
    id: int
    kind: RoomContentKind
    entity: NodeRef | None
    strength: int
    locked: bool


class RoomView(ApiModel):
    id: int
    position: int
    kind: SiteRoomKind
    challenge: SiteChallenge
    difficulty: int
    cleared_epoch: int | None
    cleared_by: NodeRef | None
    locked: list[str]
    contents: list[ContentView]


class HolderView(ApiModel):
    id: int
    holder: NodeRef | None
    from_epoch: int
    to_epoch: int | None
    how: str | None


class DigStageView(ApiModel):
    id: int
    stage: ExcavationStage
    skill: SkillKind
    technique: Technique | None
    difficulty: int
    risk: ExcavationRisk
    find: ExcavationFind
    find_item: NodeRef | None
    resolved_epoch: int | None
    locked: list[str]


class DigView(ApiModel):
    id: int
    stage: ExcavationStage
    status: ExcavationStatus
    progress: int
    leader: NodeRef | None
    sponsor: NodeRef | None
    collection_id: int | None
    collection_name: str | None
    started_epoch: int
    ended_epoch: int | None
    idle_epochs: int
    note: str | None
    locked: list[str]
    stages: list[DigStageView]


class FeatureView(ApiModel):
    id: int
    feature: BattlefieldFeature
    strength: int
    battle_id: int | None
    battle_name: str | None
    epoch: int
    locked: list[str]


class SiteView(ApiModel):
    site_id: int
    roomed: bool
    diggable: bool
    rooms: list[RoomView]
    holders: list[HolderView]
    digs: list[DigView]
    features: list[FeatureView]
