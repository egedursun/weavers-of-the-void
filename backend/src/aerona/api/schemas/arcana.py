from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.arcana import LawSource, RechargeRule, SpellDuration, SpellForm, SpellRange, SpellTarget, SpellTechnique
from aerona.domain.enums.culture import RiteEffectKind
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.mythic import (
    CosmicOffice,
    GeasLayer,
    GeasMode,
    GeasState,
    HeroquestBoon,
    HeroquestState,
    MantlingState,
    MythicRealm,
    OfficeChoice,
    QuestTrial,
    ServitorOrigin,
    ServitorRole,
)
from aerona.domain.enums.nature_kinds import OfficeDuty


class GrammarView(ApiModel):
    technique: SpellTechnique
    form: SpellForm
    range: SpellRange
    duration: SpellDuration
    target: SpellTarget
    difficulty: int
    paradigm: NodeRef | None
    myth: NodeRef | None
    locked: list[str]


class LabTextView(ApiModel):
    book: NodeRef | None
    rite: NodeRef | None
    author: NodeRef | None
    fidelity: int
    epoch: int
    locked: list[str]


class VisView(ApiModel):
    form: SpellForm
    amount: int
    locked: list[str]


class WarpingView(ApiModel):
    value: int
    stage: int
    updated_epoch: int
    locked: list[str]


class LongevityView(ApiModel):
    form: SpellForm
    dose: int
    dependence: int
    years_gained: int
    lapsed_epochs: int
    since_epoch: int
    locked: list[str]


class ChargeView(ApiModel):
    effect: RiteEffectKind
    strength: int
    charges: int
    capacity: int
    recharge: RechargeRule
    overuse: int


class UpkeepView(ApiModel):
    law: NodeRef | None
    caster: NodeRef | None
    source: LawSource
    essence_upkeep: int
    vis_form: SpellForm | None
    vis_upkeep: int
    dispel_resistance: int
    unpaid_epochs: int
    since_epoch: int
    locked: list[str]


class NodeArcanaView(ApiModel):
    node: NodeRef
    grammar: GrammarView | None
    lab_texts: list[LabTextView]
    vis: list[VisView]
    warping: WarpingView | None
    longevity: LongevityView | None
    charges: list[ChargeView]
    upkeep: UpkeepView | None
    kept: list[UpkeepView]


class HeroquestView(ApiModel):
    id: int
    quester: NodeRef | None
    legend: NodeRef | None
    god: NodeRef | None
    realm: MythicRealm
    realm_kind_id: int | None
    realm_kind_name: str | None
    place: NodeRef | None
    steps: int
    step: int
    fidelity: int
    deviated: bool
    state: HeroquestState
    boon: HeroquestBoon | None
    interference: int
    next_trial: QuestTrial | None
    members: list[NodeRef]
    start_epoch: int
    end_epoch: int | None
    locked: list[str]


class MantlingView(ApiModel):
    mortal: NodeRef | None
    god: NodeRef | None
    deeds: int
    worship: int
    progress: int
    state: MantlingState
    blocked: bool
    notified: bool
    since_epoch: int
    locked: list[str]


class ServitorView(ApiModel):
    spirit: NodeRef | None
    god: NodeRef | None
    origin: ServitorOrigin
    role: ServitorRole
    post: NodeRef | None
    loyalty: int
    fallen_to: NodeRef | None
    since_epoch: int
    locked: list[str]


class GeasView(ApiModel):
    id: int
    bearer: NodeRef | None
    layer_node: NodeRef | None
    layer: GeasLayer
    mode: GeasMode
    act: ActKind
    state: GeasState
    favour: int
    laid_epoch: int
    last_kept_epoch: int
    broken_epoch: int | None
    locked: list[str]


class CosmicOfficeView(ApiModel):
    office: CosmicOffice
    holder: NodeRef | None
    chosen_by: OfficeChoice
    since_epoch: int | None
    neglect: int
    duty: int
    office_kind_id: int | None
    office_duty: OfficeDuty
    office_name: str | None
    locked: list[str]


class NodeMythicView(ApiModel):
    node: NodeRef
    heroquests: list[HeroquestView]
    mantling: MantlingView | None
    walkers: list[MantlingView]
    servitor: ServitorView | None
    servitors: list[ServitorView]
    geasa: list[GeasView]
    laid: list[GeasView]
    offices: list[CosmicOfficeView]
