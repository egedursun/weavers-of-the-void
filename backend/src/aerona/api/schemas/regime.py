from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.cycles import LongPlanStatus
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.regime import (
    ClientRole,
    CredentialKind,
    LeadershipMode,
    LegitimacyType,
    PowerStance,
    Routinisation,
    SegmentLevel,
    SelectorateKind,
)


class RegimeView(ApiModel):
    selectorate: SelectorateKind
    selectorate_size: int
    coalition_size: int
    coalition_loyalty: int
    public_share: int
    traditional: int
    charismatic: int
    rational: int
    dominant: LegitimacyType
    founder: NodeRef | None
    ruler: NodeRef | None
    routinisation: Routinisation
    crisis_epoch: int | None
    horizon: int
    extraction: int
    institutions: int
    leadership: LeadershipMode
    rotation: bool
    parallel_guard: bool
    loyalty_promotion: bool
    hostages: bool
    updated_epoch: int
    locked: list[str]


class CoalitionMemberView(ApiModel):
    polity: NodeRef
    mortal: NodeRef
    reward: int
    loyalty: int
    since_epoch: int
    locked: list[str]


class PatronageTieView(ApiModel):
    id: int
    patron: NodeRef
    client: NodeRef
    role: ClientRole
    strength: int
    since_epoch: int
    locked: list[str]


class RealmSeatView(ApiModel):
    office_id: int
    kind: OfficeKind
    holder: NodeRef | None


class VenalOfficeView(ApiModel):
    office_id: int
    office_kind: OfficeKind
    polity: NodeRef
    holder: NodeRef | None
    price: int
    buyer: NodeRef | None
    sinecure: bool
    recouped: int
    sold_epoch: int
    locked: list[str]


class PowerBaseView(ApiModel):
    mortal: NodeRef
    polity: NodeRef | None
    holdings: int
    troops: int
    offices: int
    wealth: int
    popularity: int
    total: int
    threat: int
    stance: PowerStance
    updated_epoch: int
    locked: list[str]


class LineageSegmentView(ApiModel):
    house: NodeRef
    level: SegmentLevel
    tribe: NodeRef | None
    backs: NodeRef | None
    since_epoch: int
    locked: list[str]


class BreedingPlanView(ApiModel):
    plan_id: int
    name: str
    holder: NodeRef | None
    house: NodeRef
    locus: str | None
    allele: str | None
    target_share: int
    claim_polity: NodeRef | None
    matches: int
    love_matches: int
    barren: int
    concealed: int
    progress: int
    steps: int
    status: LongPlanStatus
    locked: list[str]


class ExaminationView(ApiModel):
    interval: int
    quota: int
    pass_mark: int
    demand: int
    last_epoch: int | None
    locked: list[str]


class ExamSittingView(ApiModel):
    id: int
    polity: NodeRef
    candidates: int
    passed: int
    mark: int
    epoch: int
    locked: list[str]


class CredentialView(ApiModel):
    id: int
    mortal: NodeRef
    kind: CredentialKind
    granter: NodeRef | None
    skill: SkillKind | None
    epoch: int
    locked: list[str]


class AcademicFreedomView(ApiModel):
    structure: NodeRef
    level: int
    orthodoxy: NodeRef | None
    suppressed: bool
    updated_epoch: int
    locked: list[str]


class DiscipleView(ApiModel):
    mortal: NodeRef
    master: NodeRef | None
    generation: int
    since_epoch: int
    locked: list[str]


class SchoolRivalView(ApiModel):
    id: int
    name: str


class SchoolView(ApiModel):
    id: int
    name: str
    doctrine: NodeRef | None
    founder: NodeRef | None
    rival: SchoolRivalView | None
    persecuted: bool
    since_epoch: int
    locked: list[str]
    disciples: list[DiscipleView]


class RegimeNodeView(ApiModel):
    node: NodeRef
    regime: RegimeView | None
    members: list[CoalitionMemberView]
    ties: list[PatronageTieView]
    seats: list[RealmSeatView]
    offices: list[VenalOfficeView]
    power_base: PowerBaseView | None
    bases: list[PowerBaseView]
    lineage: LineageSegmentView | None
    kin_lines: list[LineageSegmentView]
    breeding: list[BreedingPlanView]
    examination: ExaminationView | None
    sittings: list[ExamSittingView]
    credentials: list[CredentialView]
    freedom: AcademicFreedomView | None
    schools: list[SchoolView]


class RealmRuleView(ApiModel):
    polity: NodeRef
    selectorate: SelectorateKind
    selectorate_size: int
    coalition_size: int
    public_share: int
    horizon: int
    dominant: LegitimacyType
    routinisation: Routinisation
    leadership: LeadershipMode


class CosmosRegimeView(ApiModel):
    realms: list[RealmRuleView]
    bases: list[PowerBaseView]
    freedoms: list[AcademicFreedomView]
    schools: list[SchoolView]
    sittings: list[ExamSittingView]
