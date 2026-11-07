from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.mind import LabelView
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.genetics import DwellingKind, GiftStance, HouseholdDecision, HouseholdRole, Locus, LocusGroup
from aerona.domain.enums.society import SocialClass


class AlleleView(ApiModel):
    key: str
    label: str
    frequency: int | None = None


class LocusView(ApiModel):
    locus: Locus
    label: str
    group: LocusGroup
    group_label: str
    alleles: list[AlleleView]


class GeneView(ApiModel):
    locus: Locus
    label: str
    group: LocusGroup
    first: str
    second: str
    shown: str
    shown_label: str


class GiftView(ApiModel):
    school: str
    label: str
    aptitude: int
    gifted: bool


class LikenessView(ApiModel):
    parent: NodeRef
    likeness: int


class GenomeView(ApiModel):
    genes: list[GeneView]
    gifts: list[GiftView]
    appearance: str
    marks: list[str]
    beauty: int
    inbreeding: int
    recognisability: int
    divine_son: NodeRef | None
    likeness: list[LikenessView]
    epoch: int
    held: list[str]


class PoolView(ApiModel):
    loci: list[LocusView]
    gift_stance: GiftStance
    gift_stance_label: str
    gifted_share: int
    cohort_shares: list[LabelView]
    epoch: int
    held: list[str]


class ResemblanceView(ApiModel):
    locus: Locus
    locus_label: str
    allele: str
    allele_label: str
    share: int
    since_epoch: int
    held: list[str]


class LineageView(ApiModel):
    node_id: int
    node_kind: str
    can_hold_genome: bool
    can_hold_pool: bool
    can_hold_likeness: bool
    reason: str | None
    genome: GenomeView | None
    pool: PoolView | None
    resemblance: ResemblanceView | None
    loci: list[LocusView]
    stances: list[LabelView]


class HouseholdMemberView(ApiModel):
    mortal: NodeRef
    role: HouseholdRole
    role_label: str
    cares_for: NodeRef | None
    joined_epoch: int
    held: bool


class FurnishingView(ApiModel):
    item: NodeRef
    placed_epoch: int


class DwellingView(ApiModel):
    kind: DwellingKind
    kind_label: str
    quality: int
    effective_quality: int
    expected_quality: int
    rooms: int
    district_id: int | None
    district_label: str | None
    settlement: NodeRef | None
    furnishings: list[FurnishingView]
    built_epoch: int
    held: list[str]


class HouseholdDebtView(ApiModel):
    household_id: int
    name: str
    amount: int


class HouseholdView(ApiModel):
    id: int
    name: str
    head: NodeRef | None
    settlement: NodeRef | None
    social_class: SocialClass | None
    wealth: int
    income: int
    expenses: int
    servants: int
    dependents: int
    burden: int
    debts: list[HouseholdDebtView]
    last_decision: HouseholdDecision | None
    last_decision_label: str | None
    decided_epoch: int | None
    formed_epoch: int
    members: list[HouseholdMemberView]
    dwelling: DwellingView | None
    held: list[str]


class AggregateView(ApiModel):
    social_class: SocialClass
    social_class_label: str
    households: int
    mean_size: int
    dwelling_kind: DwellingKind
    dwelling_label: str
    quality: int
    wealth: int
    epoch: int
    held: list[str]


class HomeView(ApiModel):
    node_id: int
    node_kind: str
    can_hold_household: bool
    can_hold_aggregates: bool
    reason: str | None
    household: HouseholdView | None
    households: list[HouseholdView]
    aggregates: list[AggregateView]
    roles: list[LabelView]
    dwellings: list[LabelView]
    classes: list[LabelView]
    neighbours: list[LabelView]
