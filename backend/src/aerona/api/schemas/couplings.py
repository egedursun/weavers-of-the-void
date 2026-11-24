from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.couplings import (
    CarrionRest,
    FieldAgreementKind,
    FieldAgreementState,
    RestraintKind,
    RiteComponent,
    SealKind,
    SignCause,
    SociolectKind,
    TeachingState,
)
from aerona.domain.enums.knowledge import KnowledgeKind


class SociolectView(ApiModel):
    id: int
    language: NodeRef | None
    holder: NodeRef | None
    kind: SociolectKind
    prestige: int
    secret: bool
    salience: int
    since_epoch: int
    faded_epoch: int | None
    locked: list[str]


class SignOriginView(ApiModel):
    language: NodeRef
    community: NodeRef | None
    cause: SignCause
    since_epoch: int
    locked: list[str]


class CarrionView(ApiModel):
    carrion: int
    scavenged: int
    preserved: bool
    rest: CarrionRest
    kept: bool
    epoch: int
    locked: list[str]


class SpiritTeachingView(ApiModel):
    id: int
    teacher: NodeRef | None
    learner: NodeRef | None
    kind: KnowledgeKind
    subject: NodeRef | None
    fidelity: int
    state: TeachingState
    price: int
    epoch: int
    locked: list[str]


class ElderMemoryView(ApiModel):
    id: int
    happening: str | None
    fidelity: int
    credence: int
    epoch: int


class HappeningChoice(ApiModel):
    id: int
    name: str


class FieldAgreementView(ApiModel):
    id: int
    war_id: int | None
    kind: FieldAgreementKind
    state: FieldAgreementState
    commander: NodeRef | None
    counterpart: NodeRef | None
    place: NodeRef | None
    term_epoch: int | None
    honour: int
    epoch: int
    ended_epoch: int | None
    locked: list[str]


class WarChoice(ApiModel):
    id: int
    name: str


class SealView(ApiModel):
    id: int
    kind: SealKind
    strength: int
    decay: int
    sealer: NodeRef | None
    epoch: int
    broken_epoch: int | None
    pact_oath_id: int | None
    power_id: int | None
    living_line_id: int | None
    made_mind_id: int | None
    locked: list[str]


class SealLinkChoice(ApiModel):
    id: int
    label: str


class NoveltyView(ApiModel):
    novelty: int
    adoption: int
    peak_epoch: int | None
    revivals: int
    updated_epoch: int
    locked: list[str]


class SinecureView(ApiModel):
    id: int
    holder: NodeRef | None
    since_epoch: int


class CouplingNodeView(ApiModel):
    node: NodeRef
    is_rite: bool
    rite_parts: list[RiteComponent]
    captive_id: int | None
    restraints: list[RestraintKind]
    is_community: bool
    is_region: bool
    is_teacher: bool
    is_beast: bool
    is_place: bool
    is_fashion: bool
    is_realm: bool
    sociolects: list[SociolectView]
    signs: list[SignOriginView]
    carrion: CarrionView | None
    teachings: list[SpiritTeachingView]
    partners: list[NodeRef]
    memories: list[ElderMemoryView]
    happenings: list[HappeningChoice]
    agreements: list[FieldAgreementView]
    wars: list[WarChoice]
    seals: list[SealView]
    oath_choices: list[SealLinkChoice]
    power_choices: list[SealLinkChoice]
    line_choices: list[SealLinkChoice]
    mind_choices: list[SealLinkChoice]
    novelty: NoveltyView | None
    sinecures: list[SinecureView]
