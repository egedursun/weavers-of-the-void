from pydantic import Field

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
    name: str | None = None
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
    locked: bool = False


class HeresyView(ApiModel):
    heresy: NodeRef | None
    parent: NodeRef | None
    distance: int
    declared_epoch: int
    suppressed: bool
    tolerated: bool
    locked: list[str] = Field(default_factory=list)


class RelicView(ApiModel):
    item: NodeRef | None
    saint: NodeRef | None
    shrine: NodeRef | None
    sanctity: int
    pilgrims: int
    canonised_epoch: int
    cult: NodeRef | None = None
    locked: list[str] = Field(default_factory=list)


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
    rebirth_path: RebirthPath = RebirthPath.PEOPLE
    liturgical_language: NodeRef | None = None
    liturgy_reach: int = 100
    parent_cult: NodeRef | None = None
    devotion: int = 0
    state_realm: NodeRef | None = None
    clergy_sway: int = 0
    god_king: NodeRef | None = None
    tithe_base: list[NodeRef] = Field(default_factory=list)
    realm_population: int = 0


class StratumView(ApiModel):
    id: int
    kind: StratumKind
    name: str
    criteria: StratumCriteria
    population: int
    souls: list[NodeRef]
    realm: NodeRef | None = None
    closed: bool = False
    son_id: int | None = None
    son_name: str | None = None
    cult: NodeRef | None = None


class RealmPopulation(ApiModel):
    son_id: int
    name: str
    souls: int


class RealmOfDeadView(ApiModel):
    realm: NodeRef | None
    strata: list[StratumView]
    realms: list[NodeRef] = Field(default_factory=list)
    gods: list[RealmPopulation] = Field(default_factory=list)


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
    seal_strength: int = 0
    unrest: int = 0
    possession: PossessionView | None = None
    patron_name: str | None = None
