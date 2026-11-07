from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.mind import LabelView
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.intrigue import BeliefSource, FavourOrigin, HookDemand, HookSource, HookStrength, IdentityReason, IntrigueSecret, PlotKind, SchemePhase


class SecretView(ApiModel):
    id: int
    holder: NodeRef | None
    kind: IntrigueSecret
    label: str
    about: NodeRef | None
    severity: int
    known_by: list[NodeRef]
    source: str | None
    created_epoch: int
    exposed_epoch: int | None
    held: list[str]


class HookView(ApiModel):
    id: int
    holder: NodeRef | None
    target: NodeRef | None
    strength: HookStrength
    source: HookSource
    source_label: str
    secret_id: int | None
    created_epoch: int
    used_epoch: int | None
    last_demand: HookDemand | None
    held: bool


class FavourView(ApiModel):
    id: int
    owed_by: NodeRef | None
    owed_to: NodeRef | None
    magnitude: int
    origin: FavourOrigin
    origin_label: str
    created_epoch: int
    called_epoch: int | None
    honoured: bool | None
    held: bool


class IdentityView(ApiModel):
    false_name: str
    cover_role: str | None
    community: NodeRef | None
    reason: IdentityReason
    reason_label: str
    exposure: int
    since_epoch: int
    exposed_epoch: int | None
    held: list[str]


class SchemeView(ApiModel):
    id: int
    owner: NodeRef | None
    kind: PlotKind
    label: str
    target: NodeRef | None
    agents: list[NodeRef]
    power: int
    difficulty: int
    secrecy: int
    progress: int
    phase: SchemePhase
    phase_label: str
    discovered_by: list[NodeRef]
    started_epoch: int
    ended_epoch: int | None
    outcome: str | None
    held: list[str]


class TrueNameView(ApiModel):
    name: str
    language: NodeRef | None
    known_by: list[NodeRef]
    since_epoch: int
    held: list[str]


class KnownNameView(ApiModel):
    bearer: NodeRef
    name: str


class BeliefView(ApiModel):
    id: int
    subject: NodeRef | None
    attribute: str
    attribute_label: str
    value: int
    truth: int | None
    confidence: int
    as_of_epoch: int
    source: BeliefSource
    source_label: str
    false: bool
    held: list[str]


class IntrigueView(ApiModel):
    node_id: int
    can_hold_identity: bool
    identity_reason: str | None
    can_scheme: bool
    scheme_reason: str | None
    secrets: list[SecretView]
    known_secrets: list[SecretView]
    hooks_held: list[HookView]
    hooks_on: list[HookView]
    favours_owed: list[FavourView]
    favours_due: list[FavourView]
    identity: IdentityView | None
    schemes: list[SchemeView]
    schemes_against: list[SchemeView]
    true_name: TrueNameView | None
    names_known: list[KnownNameView]
    beliefs: list[BeliefView]
    secret_kinds: list[LabelView]
    scheme_kinds: list[LabelView]
    scheme_phases: list[LabelView]
    hook_sources: list[LabelView]
    hook_demands: list[LabelView]
    favour_origins: list[LabelView]
    identity_reasons: list[LabelView]
    belief_sources: list[LabelView]
    belief_attributes: list[LabelView]
