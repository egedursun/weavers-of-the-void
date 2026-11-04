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
    RebirthPath,
    ReincarnationGate,
    SpiritAlignment,
    StratumKind,
    TenetKind,
)
from aerona.domain.models.faith import StratumCriteria


class TenetKindSpec(ApiModel):
    tenet: TenetKind
    effect: str
    targeted: bool
    opposed: list[TenetKind]


class TenetView(ApiModel):
    tenet: TenetKind
    name: str | None
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
    locked: bool


class HeresyView(ApiModel):
    heresy: NodeRef | None
    parent: NodeRef | None
    distance: int
    declared_epoch: int
    suppressed: bool
    tolerated: bool
    locked: list[str]


class RelicView(ApiModel):
    item: NodeRef | None
    saint: NodeRef | None
    shrine: NodeRef | None
    sanctity: int
    pilgrims: int
    canonised_epoch: int
    cult: NodeRef | None
    locked: list[str]


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
    rebirth_path: RebirthPath
    liturgical_language: NodeRef | None
    liturgy_reach: int
    parent_cult: NodeRef | None
    devotion: int
    state_realm: NodeRef | None
    clergy_sway: int
    god_king: NodeRef | None
    tithe_base: list[NodeRef]
    realm_population: int


class StratumView(ApiModel):
    id: int
    kind: StratumKind
    name: str
    criteria: StratumCriteria
    population: int
    souls: list[NodeRef]
    realm: NodeRef | None
    closed: bool
    son_id: int | None
    son_name: str | None
    cult: NodeRef | None


class RealmPopulation(ApiModel):
    son_id: int
    name: str
    souls: int


class RealmOfDeadView(ApiModel):
    realm: NodeRef | None
    strata: list[StratumView]
    realms: list[NodeRef]
    gods: list[RealmPopulation]


class PossessionView(ApiModel):
    host: NodeRef | None
    spirit: NodeRef | None
    since_epoch: int
    stress: int
    host_values: dict[str, int]
    locked: list[str]


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
    seal_strength: int
    unrest: int
    possession: PossessionView | None
    patron_name: str | None
