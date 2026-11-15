from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.transform import ProspectStance, StarModifierSource, TransformEnd, TransformKind, TransformState, TransformTrigger


class KindChangeView(ApiModel):
    id: int
    kind: TransformKind
    epoch: int
    trigger: TransformTrigger
    state: TransformState
    subject: NodeRef | None
    result: NodeRef | None
    subject_name: str
    result_name: str | None
    text: str | None
    revertible: bool
    locked: list[str]


class TransformProspectView(ApiModel):
    id: int
    kind: TransformKind
    subject_id: int
    progress: int
    stance: ProspectStance
    trigger: TransformTrigger
    warned_epoch: int | None
    due_epoch: int | None
    updated_epoch: int
    locked: list[str]


class StarModifierView(ApiModel):
    id: int
    source: StarModifierSource
    luminosity_pct: int
    age_epochs: int
    aged: bool
    decay: int
    epoch: int
    cause: NodeRef | None
    locked: list[str]


class TransformNodeView(ApiModel):
    node: NodeRef
    end: TransformEnd | None
    epoch: int
    warn_epochs: int
    came_from: list[KindChangeView]
    became: list[KindChangeView]
    prospects: list[TransformProspectView]
    open_kinds: list[TransformKind]
    forceable: list[TransformKind]
    son_status: SonStatus | None
    sanity: int | None
    corruption_band: int
    body: NodeRef | None
    redeemers: list[NodeRef]
    legends: list[NodeRef]
    anchor_world: NodeRef | None
    anchor_star: NodeRef | None
    star_modifiers: list[StarModifierView]
    luminosity_shift: int
    luminosity_shift_max: int


class TransformKindView(ApiModel):
    kind: TransformKind
    source: TransformEnd
    target: TransformEnd
    existing: bool
    watched: bool
    warned: bool


class TransformTimelineView(ApiModel):
    epoch: int
    kinds: list[TransformKindView]
    transformations: list[KindChangeView]
    prospects: list[TransformProspectView]
    subjects: list[NodeRef]
