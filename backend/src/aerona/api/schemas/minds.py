from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.body import BodyPart
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.collective import AccountKind
from aerona.domain.enums.constructs import MindWill
from aerona.domain.enums.industry import EnergyKind
from aerona.domain.enums.made import (
    Attribution,
    AugmentKind,
    AugmentMake,
    AugmentSlot,
    Authenticity,
    CompanyCharter,
    CompanyHoldingKind,
    DataContent,
    EffectTarget,
    IntrusionAim,
    IntrusionApproach,
    IntrusionOutcome,
    IntrusionTarget,
    MadeMindStance,
    RealmAwareness,
    RealmEntry,
    RealmPurpose,
    RelicStance,
    RelicState,
    RelicUse,
    ReplicatorOutput,
    ReplicatorScale,
    ReplicatorStage,
    SurveillanceFocus,
)
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.minds import (
    ArchiveAccess,
    MadeMindsLaw,
    MadeMindSouls,
    MakingOutcome,
    MindAffect,
    MindMaking,
    MindOrigin,
    MindPurpose,
    MindSeat,
    MindUpkeep,
    SoulContinuity,
    StateMedium,
    WillCause,
)
from aerona.domain.enums.networks import NetworkAccess, NetworkCarrier, NetworkRole, OutageCause
from aerona.domain.enums.society import Commodity


class MindSeatPartView(ApiModel):
    id: int
    part: NodeRef | None
    share_pct: int
    vital: bool
    locked: list[str]


class MindStateView(ApiModel):
    id: int
    mind: NodeRef | None
    taken_epoch: int
    fidelity_pct: int
    holder: NodeRef | None
    medium_kind: StateMedium
    sealed: bool
    copies: int
    owner: NodeRef | None
    locked: list[str]


class MindMakingView(ApiModel):
    id: int
    maker: NodeRef | None
    method: MindMaking
    quality: int
    outcome: MakingOutcome
    epoch: int


class MindWillChangeView(ApiModel):
    id: int
    from_will: MindWill
    to_will: MindWill
    cause: WillCause
    epoch: int


class MindLineageView(ApiModel):
    kind: BondKind
    other: NodeRef
    outgoing: bool
    epoch: int


class RemoteBodyView(ApiModel):
    body: NodeRef | None
    mind: NodeRef | None
    feedback_pct: int
    since_epoch: int
    locked: list[str]


class MindArchiveView(ApiModel):
    holder: NodeRef | None
    upkeep: int
    access: ArchiveAccess
    unpaid_epochs: int
    locked: list[str]


class MindLawView(ApiModel):
    world: NodeRef
    made_minds: MadeMindsLaw
    made_mind_souls: MadeMindSouls
    soul_continuity: SoulContinuity
    locked: list[str]


class MindNodeView(ApiModel):
    node: NodeRef
    seat: MindSeat
    seat_node: NodeRef | None
    origin: MindOrigin
    will: MindWill
    affect: MindAffect
    purpose: MindPurpose
    capacity: int
    speed_pct: int
    stability: int
    fidelity_pct: int
    upkeep: MindUpkeep
    upkeep_energy: EnergyKind | None
    pausable: bool
    copyable: bool
    restorable: bool
    mergeable: bool
    transferable: bool
    dormant: bool
    perfect_recall: bool
    souled: bool
    made_by: NodeRef | None
    maker_bond: int
    drift_pct: int
    run_epochs: int
    locked: list[str]
    seats: list[MindSeatPartView]
    states: list[MindStateView]
    makings: list[MindMakingView]
    will_changes: list[MindWillChangeView]
    lineage: list[MindLineageView]
    remote_bodies: list[RemoteBodyView]
    archive: MindArchiveView | None
    law: MindLawView | None
    speed_max: int
    soul_grant_cost: int


class NetworkProfileView(ApiModel):
    carrier: NetworkCarrier
    access: NetworkAccess
    carries_messages: bool
    carries_records: bool
    carries_control: bool
    carries_money: bool
    carries_minds: bool
    carries_opinion: bool
    capacity: int
    delay_days: int
    security: int
    reliability: int
    curation: int
    censorship: int
    owner: NodeRef | None
    tech_level: int
    down_until_epoch: int
    founded_epoch: int
    running: bool
    locked: list[str]


class NetworkMemberView(ApiModel):
    id: int
    network: NodeRef | None
    member: NodeRef | None
    role: NetworkRole
    dependency_pct: int
    security: int
    joined_epoch: int
    locked: list[str]


class NetworkGatewayView(ApiModel):
    id: int
    first: NodeRef | None
    second: NodeRef | None
    toll: int
    filter_pct: int
    owner: NodeRef | None
    locked: list[str]


class NetworkOutageView(ApiModel):
    id: int
    cause: OutageCause
    epoch: int
    epochs: int
    severity: int


class NetworkNodeView(ApiModel):
    node: NodeRef
    profile: NetworkProfileView | None
    members: list[NetworkMemberView]
    gateways: list[NetworkGatewayView]
    outages: list[NetworkOutageView]
    memberships: list[NetworkMemberView]


class AugmentEffectView(ApiModel):
    id: int
    target: EffectTarget
    target_key: str
    amount: int
    locked: list[str]


class AugmentView(ApiModel):
    id: int
    slot: AugmentSlot
    part: BodyPart | None
    kind: AugmentKind
    make: AugmentMake
    quality: int
    upkeep: MindUpkeep
    integration: int
    strain: int
    installed_by: NodeRef | None
    installed_epoch: int
    locked: list[str]
    effects: list[AugmentEffectView]


class AugmentsNodeView(ApiModel):
    node: NodeRef
    bears: bool
    reason: str | None
    augments: list[AugmentView]


class IntrusionView(ApiModel):
    id: int
    actor: NodeRef | None
    target: IntrusionTarget
    target_node: NodeRef | None
    approach: IntrusionApproach
    aim: IntrusionAim
    stealth: int
    detection: int
    attribution: Attribution
    blamed: NodeRef | None
    outcome: IntrusionOutcome
    epoch: int
    locked: list[str]


class DataContentView(ApiModel):
    id: int
    content: DataContent
    subject: NodeRef | None
    reference: int | None
    epoch: int
    locked: list[str]


class DataStoreView(ApiModel):
    id: int
    holder: NodeRef | None
    security: int
    owner: NodeRef | None
    locked: list[str]
    contents: list[DataContentView]


class SurveillanceView(ApiModel):
    capacity: int
    reach_pct: int
    focus: SurveillanceFocus
    updated_epoch: int
    locked: list[str]


class TrustView(ApiModel):
    information_trust: int
    shared_account_pct: int
    updated_epoch: int
    locked: list[str]


class CompanyHoldingView(ApiModel):
    id: int
    holding: NodeRef | None
    kind: CompanyHoldingKind
    locked: list[str]


class CompanyPresenceView(ApiModel):
    company: NodeRef | None
    polity: NodeRef | None
    licensed: bool
    influence: int
    locked: list[str]


class EnclaveView(ApiModel):
    settlement: NodeRef | None
    company: NodeRef | None
    since_epoch: int
    locked: list[str]


class CompanyPowerView(ApiModel):
    charter: CompanyCharter
    headquarters: NodeRef | None
    locked: list[str]
    holdings: list[CompanyHoldingView]
    presences: list[CompanyPresenceView]
    enclaves: list[EnclaveView]


class ReplicatorPresenceView(ApiModel):
    id: int
    line_id: int
    line_name: str
    place: NodeRef | None
    mass: int
    growth: int
    locked: list[str]


class ReplicatorLineView(ApiModel):
    id: int
    name: str
    scale: ReplicatorScale
    feedstock: MaterialKind
    output: ReplicatorOutput
    growth_pct: int
    error_pct: int
    containment: int
    kill_switch: bool
    owner: NodeRef | None
    maker: NodeRef | None
    mind: NodeRef | None
    stage: ReplicatorStage
    founded_epoch: int
    locked: list[str]
    presences: list[ReplicatorPresenceView]


class FabricationView(ApiModel):
    share_pct: int
    dividend_pct: int
    updated_epoch: int
    locked: list[str]


class ScarcityView(ApiModel):
    commodity: Commodity
    scarcity: int
    updated_epoch: int
    locked: list[str]


class PatternRightView(ApiModel):
    id: int
    commodity: Commodity
    holder: NodeRef | None
    licence_fee: int
    open: bool
    since_epoch: int
    locked: list[str]


class MadeRelicView(ApiModel):
    make_knowledge: int
    repair_knowledge: int
    function_state: RelicState
    understood_pct: int
    use: RelicUse
    is_relic: bool
    updated_epoch: int
    locked: list[str]


class SalvageView(ApiModel):
    yield_left: int
    rights_holder: NodeRef | None
    last_salvaged_epoch: int | None
    locked: list[str]


class SubstrateView(ApiModel):
    seat: MindSeat
    origin: MindOrigin
    share_pct: int
    locked: list[str]


class MadeRealmView(ApiModel):
    dimension: NodeRef
    host: NodeRef | None
    keeper: NodeRef | None
    realm_purpose: RealmPurpose
    time_ratio_pct: int
    fidelity: int
    entry: RealmEntry
    aware_inside: RealmAwareness
    upkeep: MindUpkeep
    frozen_until_epoch: int
    sealed: bool
    locked: list[str]
    minds_inside: int


class DoctrineStancesView(ApiModel):
    made_mind_stance: MadeMindStance
    copy_stance: MadeMindStance
    augment_stance: MadeMindStance
    made_afterlife_stance: MadeMindStance
    relic_stance: RelicStance
    locked: list[str]


class RecordTrustView(ApiModel):
    id: int
    kind: AccountKind
    subject: NodeRef | None
    author: NodeRef | None
    authenticity: Authenticity
    credence: int
    epoch: int


class MadeWorldNodeView(ApiModel):
    node: NodeRef
    intrusions: list[IntrusionView]
    stores: list[DataStoreView]
    surveillance: SurveillanceView | None
    trust: TrustView | None
    company: CompanyPowerView | None
    enclave: EnclaveView | None
    lines: list[ReplicatorLineView]
    presences: list[ReplicatorPresenceView]
    fabrication: FabricationView | None
    scarcity: list[ScarcityView]
    patterns: list[PatternRightView]
    relic: MadeRelicView | None
    salvage: SalvageView | None
    substrates: list[SubstrateView]
    realms: list[MadeRealmView]
    doctrine: DoctrineStancesView | None
    records: list[RecordTrustView]
