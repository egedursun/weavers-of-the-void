from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.collective import ArmsInk
from aerona.domain.enums.demography import SexKind
from aerona.domain.enums.entity import MortalRole
from aerona.domain.enums.mind import KindFamily, Profession
from aerona.domain.enums.mortal import CareerPath, DeathCause, EquipmentSlot, LifeStage, MarriageEnd, StressBreak
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.unions import UnionForm, UnionPurpose


class MarriageView(ApiModel):
    id: int
    spouse: NodeRef | None
    form: UnionForm
    purpose: UnionPurpose
    treaty: NodeRef | None
    start_epoch: int
    end_epoch: int | None
    cause_end: MarriageEnd | None
    forced: bool


class KinLink(ApiModel):
    bond_id: int
    kind: BondKind
    other: NodeRef
    outgoing: bool
    living: bool


class SlotView(ApiModel):
    slot: EquipmentSlot
    item: NodeRef | None
    held: bool


class MortalProfileView(ApiModel):
    mortal: NodeRef
    sex: SexKind
    life_stage: LifeStage
    fertility: int
    health: int
    stress: int
    wealth: int
    renown: int
    honour: int
    infamy: int
    legitimacy: int | None
    education: int
    polity: NodeRef | None
    loyalty_liege: int
    loyalty_community: int
    loyalty_god: int
    career: CareerPath | None
    profession: Profession | None
    last_break: StressBreak | None
    last_break_epoch: int | None
    cause_of_death: DeathCause | None
    death_place: NodeRef | None
    social_class: SocialClass | None
    held: list[str]
    marriages: list[MarriageView]
    kin: list[KinLink]
    equipment: list[SlotView]
    stress_threshold: int


class VariantView(ApiModel):
    id: int
    family: KindFamily
    base: str
    name: str
    description: str | None
    strength_pct: int
    learning_pct: int
    held: list[str]


class TreeHouse(ApiModel):
    house: NodeRef
    ink: ArmsInk | None


class TreePerson(ApiModel):
    id: int
    name: str
    title: str | None
    relation: str
    living: bool
    sex: SexKind | None
    role: MortalRole | None
    generation: int
    birth_epoch: int
    end_epoch: int | None
    cover: str | None
    house_id: int | None
    blood: bool


class TreeUnion(ApiModel):
    marriage_id: int
    first_id: int
    second_id: int
    form: UnionForm
    purpose: UnionPurpose
    start_epoch: int
    end_epoch: int | None
    cause_end: MarriageEnd | None
    forced: bool


class TreeTie(ApiModel):
    bond_id: int
    kind: BondKind
    source_id: int
    target_id: int
    past: bool
    epoch: int


class TreeCard(ApiModel):
    person_id: int
    x: float
    y: float


class TreePartner(ApiModel):
    key: str
    first_id: int
    second_id: int
    kind: BondKind
    ended: bool
    widowed: bool
    marriage_id: int | None
    bond_id: int | None
    path: str
    knot_x: float
    knot_y: float


class TreeFamily(ApiModel):
    key: str
    parent_ids: list[int]
    child_ids: list[int]
    path: str


class TreeCare(ApiModel):
    bond_id: int
    path: str


class TreeRow(ApiModel):
    generation: int
    y: float


class TreeLayout(ApiModel):
    width: float
    height: float
    card_width: int
    card_height: int
    cards: list[TreeCard]
    partners: list[TreePartner]
    families: list[TreeFamily]
    care: list[TreeCare]
    rows: list[TreeRow]


class FamilyTreeView(ApiModel):
    root: int
    up: int
    down: int
    deeper_up: bool
    deeper_down: bool
    people: list[TreePerson]
    houses: list[TreeHouse]
    unions: list[TreeUnion]
    ties: list[TreeTie]
    layout: TreeLayout
