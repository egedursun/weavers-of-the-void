from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.agrarian import (
    AidKind,
    CentralityRank,
    CommonsKind,
    CommonsRule,
    KeystoneUse,
    LandUseRing,
    NutrientKind,
    PerennialKind,
    PreparednessKind,
    RebuildCause,
    RebuildPlan,
)
from aerona.domain.enums.economy import CommodityKind, WorkshopKind


class LandRingView(ApiModel):
    region: NodeRef
    market: NodeRef | None
    ring: LandUseRing
    distance: int
    by_water: bool
    gap: int
    updated_epoch: int
    locked: list[str]


class CentralPlaceView(ApiModel):
    settlement: NodeRef
    rank: CentralityRank
    catchment: int
    served_by: NodeRef | None
    centrality: int
    updated_epoch: int
    locked: list[str]


class SoilNutrientView(ApiModel):
    nutrient: NutrientKind
    stock: int
    trend: int
    updated_epoch: int
    locked: list[str]


class IntensificationView(ApiModel):
    pressure: int
    intensity: int
    research_boost: int
    updated_epoch: int
    locked: list[str]


class PerennialView(ApiModel):
    id: int
    region: NodeRef
    kind: PerennialKind
    species: NodeRef | None
    owner: NodeRef | None
    area: int
    maturity: int
    mature_epochs: int
    condition: int
    planted_epoch: int
    felled_epoch: int | None
    locked: list[str]


class CommonsView(ApiModel):
    id: int
    region: NodeRef
    kind: CommonsKind
    rule: CommonsRule
    condition: int
    use: int
    steward: NodeRef | None
    encloser: NodeRef | None
    enclosed_epoch: int | None
    dispossessed: int
    since_epoch: int
    locked: list[str]


class GameReserveView(ApiModel):
    id: int
    region: NodeRef
    holder: NodeRef | None
    species: NodeRef | None
    strictness: int
    poaching: int
    resentment: int
    since_epoch: int
    locked: list[str]


class FamineLoreView(ApiModel):
    people: NodeRef
    memory: int
    famine_foods: bool
    storage: int
    updated_epoch: int
    locked: list[str]


class PreparednessView(ApiModel):
    settlement: NodeRef
    kind: PreparednessKind
    level: int
    condition: int
    averted: int
    built_epoch: int
    locked: list[str]


class ReliefAidView(ApiModel):
    id: int
    event: NodeRef | None
    giver: NodeRef
    receiver: NodeRef
    kind: AidKind
    amount: int
    god: NodeRef | None
    refused: bool
    epoch: int
    locked: list[str]


class ReconstructionView(ApiModel):
    id: int
    settlement: NodeRef
    cause: RebuildCause
    plan: RebuildPlan
    cost: int
    paid: int
    progress: int
    planner: NodeRef | None
    seized_by: NodeRef | None
    seized: int
    started_epoch: int
    finished_epoch: int | None
    locked: list[str]


class KeystoneView(ApiModel):
    id: int
    world: NodeRef
    name: str
    producer: NodeRef | None
    source: NodeRef | None
    commodity: CommodityKind | None
    use: KeystoneUse
    cult: NodeRef | None
    controller: NodeRef | None
    harvest: int
    supply: int
    price: int
    designated_epoch: int
    designated_by: NodeRef | None
    locked: list[str]


class BrandView(ApiModel):
    id: int
    workshop_id: int
    workshop_kind: WorkshopKind
    community: NodeRef
    owner: NodeRef | None
    name: str
    reputation: int
    quality: int
    renowned: int
    counterfeits: int
    since_epoch: int
    locked: list[str]


class UnbrandedWorkshopView(ApiModel):
    id: int
    kind: WorkshopKind
    level: int


class AgrarianNodeView(ApiModel):
    node: NodeRef
    world: NodeRef | None
    ring: LandRingView | None
    nutrients: list[SoilNutrientView]
    intensity: IntensificationView | None
    perennials: list[PerennialView]
    commons: list[CommonsView]
    reserves: list[GameReserveView]
    famine: FamineLoreView | None
    central_place: CentralPlaceView | None
    works: list[PreparednessView]
    aid: list[ReliefAidView]
    rebuilds: list[ReconstructionView]
    keystones: list[KeystoneView]
    brands: list[BrandView]
    workshops: list[UnbrandedWorkshopView]


class CosmosAgrarianView(ApiModel):
    rings: list[LandRingView]
    central_places: list[CentralPlaceView]
    keystones: list[KeystoneView]
    brands: list[BrandView]
    aid: list[ReliefAidView]
    rebuilds: list[ReconstructionView]
    commons: list[CommonsView]
    reserves: list[GameReserveView]
