from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.cycles import (
    AdoptionKind,
    ChallengeKind,
    ChallengeResponse,
    CyclePhase,
    DescentGroup,
    GiftOccasion,
    GiftState,
    KinshipDescent,
    KinTermSystem,
    LabourRegime,
    LegacyKind,
    LongPlanKind,
    LongPlanStatus,
    ManumissionPath,
    MobilityMode,
    ReproductiveCaste,
    ReproductiveSystem,
    ResidenceRule,
    StressComponent,
)
from aerona.domain.enums.demography import Sex
from aerona.domain.enums.unions import (
    KinMatch,
    PartnerScope,
    PluralSide,
    UnionArrangement,
    UnionDescent,
    UnionDissolution,
    UnionExchange,
    UnionForm,
    UnionPurpose,
    UnionResidence,
)


class StressPartView(ApiModel):
    component: StressComponent
    value: int


class StressView(ApiModel):
    parts: list[StressPartView]
    psi: int
    aspirants: int
    positions: int
    challenge: int
    phase: CyclePhase
    updated_epoch: int
    locked: list[str]


class ReadingView(ApiModel):
    epoch: int
    pressure: int
    immiseration: int
    elite_overproduction: int
    fiscal_distress: int
    psi: int
    phase: CyclePhase


class SolidarityView(ApiModel):
    value: int
    frontier: int
    luxury_generations: int
    conflict: int
    updated_epoch: int
    locked: list[str]


class ChallengeView(ApiModel):
    id: int
    kind: ChallengeKind
    severity: int
    response: ChallengeResponse
    source: NodeRef | None
    epoch: int


class PlanView(ApiModel):
    id: int
    holder: NodeRef
    author: NodeRef | None
    carrier: NodeRef | None
    target: NodeRef | None
    kind: LongPlanKind
    name: str
    steps: int
    progress: int
    step_cost: int
    secrecy: int
    exposed: bool
    status: LongPlanStatus
    started_epoch: int
    finished_epoch: int | None
    locked: list[str]


class GiftRecordView(ApiModel):
    id: int
    giver: NodeRef
    receiver: NodeRef
    value: int
    occasion: GiftOccasion
    item: NodeRef | None
    state: GiftState
    answers_gift_id: int | None
    due_epoch: int | None
    settled_epoch: int | None
    epoch: int
    locked: list[str]


class CircuitView(ApiModel):
    id: int
    name: str
    item: NodeRef | None
    stops: list[NodeRef]
    position: int
    passes: int
    started_epoch: int
    locked: list[str]


class OfferingLedgerView(ApiModel):
    god: NodeRef
    community: NodeRef
    offered: int
    answered: int
    last_offering_epoch: int | None
    last_answer_epoch: int | None
    locked: list[str]


class KinshipView(ApiModel):
    descent: KinshipDescent
    residence: ResidenceRule
    descent_group: DescentGroup
    kin_terms: KinTermSystem
    adoption: AdoptionKind
    first_side: Sex
    sibling_union_first: bool
    sibling_union_second: bool
    locked: list[str]


class UnionView(ApiModel):
    form: UnionForm
    plural_side: PluralSide
    purpose: UnionPurpose
    residence: UnionResidence
    descent: UnionDescent
    exchange: UnionExchange
    exchange_value: int
    arrangement: UnionArrangement
    dissolution: UnionDissolution
    endogamy: PartnerScope
    exogamy: PartnerScope
    kin_match: KinMatch
    term_epochs: int
    locked: list[str]


class AllianceView(ApiModel):
    giver: NodeRef
    taker: NodeRef
    marriages: int
    treaty: NodeRef | None
    since_epoch: int
    last_epoch: int
    locked: list[str]


class ReproductionView(ApiModel):
    system: ReproductiveSystem
    change_age: int
    breeder_pct: int
    soldier_pct: int
    worker_pct: int
    locked: list[str]


class CasteView(ApiModel):
    caste: ReproductiveCaste
    since_epoch: int
    locked: list[str]


class CampView(ApiModel):
    mode: MobilityMode
    circuit: list[NodeRef]
    season_index: int
    herd: int
    grazing: int
    water: int
    last_moved_epoch: int | None
    locked: list[str]


class ConfederationView(ApiModel):
    id: int
    name: str
    leader: NodeRef | None
    members: list[NodeRef]
    formed_epoch: int
    dissolved_epoch: int | None
    locked: list[str]


class LegacyView(ApiModel):
    kind: LegacyKind
    key: str
    key_label: str
    predecessor: NodeRef | None
    since_epoch: int
    locked: list[str]


class IndentureView(ApiModel):
    id: int
    employer: NodeRef | None
    regime: LabourRegime
    count: int
    term_epochs: int
    debt: int
    exploitation: int
    origin: NodeRef | None
    since_epoch: int
    locked: list[str]


class BondMarketView(ApiModel):
    price: int
    stock: int
    sold: int
    open: bool
    updated_epoch: int
    locked: list[str]


class ManumissionView(ApiModel):
    id: int
    count: int
    path: ManumissionPath
    standing: int
    origin: NodeRef | None
    epoch: int
    locked: list[str]


class CyclesView(ApiModel):
    node: NodeRef
    stress: StressView | None
    readings: list[ReadingView]
    solidarity: SolidarityView | None
    challenges: list[ChallengeView]
    plans: list[PlanView]
    gifts: list[GiftRecordView]
    gift_balance: int
    debts: list[OfferingLedgerView]
    circuits: list[CircuitView]
    kinship: KinshipView | None
    union: UnionView | None
    alliances: list[AllianceView]
    reproduction: ReproductionView | None
    caste: CasteView | None
    camp: CampView | None
    confederations: list[ConfederationView]
    legacies: list[LegacyView]
    indentures: list[IndentureView]
    market: BondMarketView | None
    manumissions: list[ManumissionView]


class FrontierView(ApiModel):
    holder: NodeRef
    value: int
    frontier: int
    conflict: int
    regions: list[NodeRef]


class RealmCycleView(ApiModel):
    polity: NodeRef
    psi: int
    phase: CyclePhase
    challenge: int
    readings: list[ReadingView]


class CosmosCyclesView(ApiModel):
    realms: list[RealmCycleView]
    frontiers: list[FrontierView]
    circuits: list[CircuitView]
    confederations: list[ConfederationView]
    plans: list[PlanView]
    gifts: list[GiftRecordView]
