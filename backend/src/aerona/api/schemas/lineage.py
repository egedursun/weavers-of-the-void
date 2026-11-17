from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.mind import LabelView
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.genetics import DwellingTenure, GeneticEffect, GiftStance, HouseholdDecision, HouseholdForm, HouseholdRole, Locus, LocusGroup
from aerona.domain.enums.industry import EnergyKind
from aerona.domain.enums.mind import TraitKind
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.urban import HousingLevel


class AlleleView(ApiModel):
    key: str
    label: str
    frequency: int | None = None
    effects: list[str]


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
    group_label: str
    first: str
    second: str
    shown: str
    shown_label: str
    effects: list[str]


class TiedTraitView(ApiModel):
    trait: TraitKind
    trait_label: str
    locus: Locus
    locus_label: str
    held: bool


class CarriedAlleleView(ApiModel):
    locus: Locus
    locus_label: str
    allele: str
    allele_label: str
    harmful: bool


class BloodEffectView(ApiModel):
    effect: GeneticEffect
    label: str
    amount: int
    per_epoch: bool


class GiftView(ApiModel):
    school: MagicSchool
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
    potential: dict[str, int]
    divine_son: NodeRef | None
    likeness: list[LikenessView]
    tied_traits: list[TiedTraitView]
    carried: list[CarriedAlleleView]
    blood_effects: list[BloodEffectView]
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
    node_kind: EntityType | NodeKind
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


class DwellingKindOption(ApiModel):
    id: int
    name: str
    level: HousingLevel
    built_in: bool


class DwellingView(ApiModel):
    dwelling_kind_id: int | None
    kind_name: str
    level: HousingLevel
    quality: int
    effective_quality: int
    expected_quality: int
    rooms: int
    district_id: int | None
    district_kind: DistrictKind | None
    settlement: NodeRef | None
    furnishings: list[FurnishingView]
    tenure: DwellingTenure
    heating: EnergyKind | None
    light: EnergyKind | None
    crowding: int
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
    form: HouseholdForm
    members: list[HouseholdMemberView]
    dwelling: DwellingView | None
    held: list[str]


class AggregateView(ApiModel):
    social_class: SocialClass
    social_class_label: str
    households: int
    mean_size: int
    dwelling_kind_id: int | None
    dwelling_name: str
    dwelling_level: HousingLevel
    quality: int
    wealth: int
    epoch: int
    held: list[str]


class HomeView(ApiModel):
    node_id: int
    node_kind: EntityType | NodeKind
    can_hold_household: bool
    can_hold_aggregates: bool
    reason: str | None
    household: HouseholdView | None
    households: list[HouseholdView]
    aggregates: list[AggregateView]
    roles: list[LabelView]
    dwellings: list[DwellingKindOption]
    classes: list[LabelView]
    neighbours: list[LabelView]
