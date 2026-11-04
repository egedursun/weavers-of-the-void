from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.faith import (
    AfterlifeState,
    BindingKind,
    ClergyOffice,
    FanaticismKind,
    FuneralRite,
    HoldingKind,
    JudgementDoctrine,
    ReincarnationGate,
    SpiritAlignment,
    StratumKind,
    TenetKind,
)


class TenetKindSpec(ApiModel):
    tenet: TenetKind
    effect: str
    targeted: bool
    opposed: list[TenetKind]


class TenetView(ApiModel):
    tenet: TenetKind
    effect: str
    target: str | None
    target_name: str | None
    since_epoch: int
    revealed_by_son_id: int | None


class HoldingView(ApiModel):
    kind: HoldingKind
    holding: NodeRef | None
    since_epoch: int


class ClergyView(ApiModel):
    kind: ClergyOffice
    holder: NodeRef | None
    since_epoch: int


class HeresyView(ApiModel):
    heresy: NodeRef | None
    parent: NodeRef | None
    distance: int
    declared_epoch: int
    suppressed: bool
    tolerated: bool


class RelicView(ApiModel):
    item: NodeRef | None
    saint: NodeRef | None
    shrine: NodeRef | None
    sanctity: int
    pilgrims: int
    canonised_epoch: int


class DoctrineView(ApiModel):
    cult: NodeRef | None
    god: NodeRef | None
    judgement: JudgementDoctrine
    orthodoxy: int
    tithe_rate: int
    treasury: int
    clergy_count: int
    clergy_quality: int
    zeal: int
    zeal_parts: dict[str, int]
    fanaticism: FanaticismKind | None
    fanaticism_epoch: int | None
    doctrinal_distance: int
    excommunicated: list[NodeRef]
    members: list[NodeRef]
    locked: list[str]
    tenets: list[TenetView]
    holdings: list[HoldingView]
    clergy: list[ClergyView]
    heresies: list[HeresyView]
    mother: HeresyView | None
    relics: list[RelicView]


class StratumView(ApiModel):
    id: int
    kind: StratumKind
    name: str
    criteria: dict[str, int | str]
    population: int
    souls: list[NodeRef]


class RealmOfDeadView(ApiModel):
    realm: NodeRef | None
    strata: list[StratumView]


class JudgementView(ApiModel):
    epoch: int
    doctrine: JudgementDoctrine
    stratum: str | None
    score: int
    rite: FuneralRite
    reason: str


class SoulCard(ApiModel):
    spirit: NodeRef | None
    origin: NodeRef | None
    patron_son_id: int | None
    state: AfterlifeState
    alignment: SpiritAlignment
    binding: BindingKind
    bound: NodeRef | None
    rite: FuneralRite
    sealed: bool
    memory_strength: int
    veneration: int
    imprint: dict[str, int]
    traits: list[str]
    deeds: dict[str, int]
    stratum: StratumView | None
    judgements: list[JudgementView]
    possessing: NodeRef | None
    reborn_as: NodeRef | None
    gate: ReincarnationGate | None
    locked: list[str]
