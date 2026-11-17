from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.crafts import (
    AffinityMode,
    AssistiveAid,
    CatchGround,
    CatchRight,
    ChemicalProduct,
    ClockKind,
    Gear,
    InsuranceCover,
    LinkToken,
    Notation,
    RightAcquired,
    RightKind,
)
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.mind import Emotion


class GroundView(ApiModel):
    source: NodeRef
    region: NodeRef
    ground: CatchGround
    gear: Gear
    right: CatchRight
    owner: NodeRef | None
    effort: int
    collapse_at: int
    collapsed: bool
    last_catch: int
    first_stock: int
    locked: list[str]


class ChemicalWorksView(ApiModel):
    settlement: NodeRef
    product: ChemicalProduct
    output: int
    hazard: int
    pollution: int
    accidents: int
    founded_epoch: int
    locked: list[str]


class InsurerView(ApiModel):
    insurer: NodeRef
    pool: int
    risk_belief: int
    premium_pct: int
    ruined: bool
    claims_seen: int
    locked: list[str]


class InsurancePolicyView(ApiModel):
    id: int
    insurer: NodeRef
    holder: NodeRef
    cover: InsuranceCover
    premium: int
    sum_insured: int
    active: bool
    since_epoch: int
    claims: int
    locked: list[str]


class HeldRightView(ApiModel):
    id: int
    holder: NodeRef
    kind: RightKind
    subject: NodeRef | None
    name: str
    acquired: RightAcquired
    licensed_to: NodeRef | None
    since_epoch: int
    locked: list[str]


class AidView(ApiModel):
    kind: AssistiveAid
    quality: int
    since_epoch: int
    locked: list[str]


class ClockView(ApiModel):
    kind: ClockKind
    precision: int
    built_epoch: int
    locked: list[str]


class NumbersView(ApiModel):
    base: int
    notation: Notation
    zero: bool
    numeracy: int
    locked: list[str]


class AffinityView(ApiModel):
    material_id: int
    material: str
    school: MagicSchool
    mode: AffinityMode
    power: int
    locked: list[str]


class LinkView(ApiModel):
    id: int
    holder: NodeRef
    target: NodeRef
    token: LinkToken
    strength: int
    obtained_epoch: int
    locked: list[str]


class SpiritView(ApiModel):
    id: int
    region: NodeRef
    emotion: Emotion
    strength: int
    born_epoch: int
    lifetime: int
    bound_by: NodeRef | None
    locked: list[str]


class AffinityMaterialChoice(ApiModel):
    id: int
    name: str


class CraftsNodeView(ApiModel):
    node: NodeRef
    people: NodeRef | None
    region: NodeRef | None
    grounds: list[GroundView]
    works: list[ChemicalWorksView]
    insurer: InsurerView | None
    policies: list[InsurancePolicyView]
    rights: list[HeldRightView]
    aids: list[AidView]
    clock: ClockView | None
    numbers: NumbersView | None
    affinities: list[AffinityView]
    links: list[LinkView]
    spirits: list[SpiritView]
    materials: list[AffinityMaterialChoice]
