from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.customs import (
    AgeGrade,
    CoopPurpose,
    EvidenceKind,
    GradeDuty,
    Intoxicant,
    IntoxicantUse,
    MarkKind,
    MarkMeaning,
    Membership,
    NameForm,
    NamingPattern,
    Naturalisation,
    ReliefKind,
    RevivalGoal,
    RevivalStage,
    RevivalWay,
)
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.society import SocialClass


class RevivalView(ApiModel):
    id: int
    dominant: NodeRef | None
    way: RevivalWay
    stage: RevivalStage
    goal: RevivalGoal
    strength: int
    prophet: NodeRef | None
    started_epoch: int
    ended_epoch: int | None
    locked: list[str]


class IntoxicantView(ApiModel):
    intoxicant: Intoxicant
    use: IntoxicantUse
    acceptance: int
    locked: list[str]


class MarkCustomView(ApiModel):
    kind: MarkKind
    meaning: MarkMeaning
    locked: list[str]


class BodyMarkView(ApiModel):
    id: int
    kind: MarkKind
    meaning: MarkMeaning
    augment_id: int | None
    placed_epoch: int
    locked: list[str]


class GradeDutyView(ApiModel):
    duty: GradeDuty
    grade: AgeGrade
    held: bool


class TimeBudgetView(ApiModel):
    social_class: SocialClass
    life_stage: LifeStage
    work: int
    rest: int
    worship: int
    leisure: int
    travel: int
    service: int
    learning: int
    care: int
    art: int
    housework: int
    sleep: int
    civic: int
    training: int
    locked: list[str]


class NamingCustomView(ApiModel):
    pattern: NamingPattern
    secret_names: bool
    taboo_epochs: int
    rename_on_initiation: bool
    rename_on_marriage: bool
    rename_on_vow: bool
    posthumous_names: bool
    locked: list[str]


class NameFormView(ApiModel):
    form: NameForm
    name: str
    given_epoch: int
    locked: list[str]


class AgeSetView(ApiModel):
    id: int
    name: str
    initiated_from: int
    initiated_to: int | None
    grade: AgeGrade
    promoted_epoch: int
    members: int
    locked: list[str]


class TavernView(ApiModel):
    structure: NodeRef
    keeper: NodeRef | None
    patrons: int
    brawls: int
    lodging: int
    rumours: int
    locked: list[str]


class WelfareView(ApiModel):
    structure: NodeRef
    patron: NodeRef | None
    inmates: int
    upkeep: int
    locked: list[str]


class CommuteView(ApiModel):
    distance: int
    labour_lost: int
    worker_camp: bool
    updated_epoch: int
    locked: list[str]


class CooperativeView(ApiModel):
    purpose: CoopPurpose
    pool: int
    members: int
    locked: list[str]


class EvidenceView(ApiModel):
    id: int
    case_id: int
    kind: EvidenceKind
    points_to: NodeRef | None
    reliability: int
    forged: bool
    found_epoch: int
    locked: list[str]


class CategoryView(ApiModel):
    category: Membership
    rights: list[str]
    locked: list[str]


class MembershipView(ApiModel):
    realm: NodeRef
    category: Membership
    path: Naturalisation
    since_epoch: int
    locked: list[str]


class BorderView(ApiModel):
    fee: int
    delay: int
    enforcement: int
    corruption: int
    locked: list[str]


class ReliefView(ApiModel):
    kind: ReliefKind
    budget: int
    reach: int
    locked: list[str]


class MeasureView(ApiModel):
    standard: bool
    adopted_epoch: int
    fraud: int
    locked: list[str]


class CustomsNodeView(ApiModel):
    node: NodeRef
    people: NodeRef | None
    revivals: list[RevivalView]
    intoxicants: list[IntoxicantView]
    mark_customs: list[MarkCustomView]
    marks: list[BodyMarkView]
    budgets: list[TimeBudgetView]
    naming: NamingCustomView | None
    names: list[NameFormView]
    age_sets: list[AgeSetView]
    grade_duties: list[GradeDutyView]
    age_set_id: int | None
    taverns: list[TavernView]
    welfare: list[WelfareView]
    commute: CommuteView | None
    cooperative: CooperativeView | None
    evidence: list[EvidenceView]
    categories: list[CategoryView]
    membership: MembershipView | None
    border: BorderView | None
    relief: ReliefView | None
    measures: MeasureView | None
