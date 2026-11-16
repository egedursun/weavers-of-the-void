from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.arcana import SpellForm, SpellTechnique
from aerona.domain.enums.concealment import BreachCause, ConcealScope, HiddenTruthKind, KeeperResponse, KeeperRole, SeekerAim, TruthAttitude
from aerona.domain.enums.culture import MagicSource, RiteEffectKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.powers import (
    BloodlineRule,
    GiftedAttitude,
    GiftedStance,
    Learnability,
    PowerCost,
    PowerHazard,
    PowerOrigin,
    PowerState,
    PowerStructure,
    PowerTrigger,
    PowerVisibility,
    ResistanceKind,
    RestrictionKind,
    SourceAccess,
    SourceLawLevel,
    SourceLocus,
    SourceRelation,
    SourceRenewal,
    SystemRelation,
    TideCycle,
)


class PowerRestrictionView(ApiModel):
    id: int
    kind: RestrictionKind
    ref: NodeRef | None
    detail: str | None
    strength_gain_pct: int
    broken: bool
    locked: list[str]


class PowerTriggerView(ApiModel):
    id: int
    trigger: PowerTrigger
    locked: list[str]


class PowerSpanView(ApiModel):
    id: int
    effect: RiteEffectKind
    target: NodeRef | None
    amount: int
    until_epoch: int
    locked: list[str]


class PowerView(ApiModel):
    id: int
    holder: NodeRef
    system_id: int | None
    system_name: str | None
    source_id: int | None
    source_name: str | None
    technique: SpellTechnique
    form: SpellForm
    range_km: int
    duration_days: int
    on_others: bool
    strength: int
    control: int
    origin: PowerOrigin
    state: PowerState
    visibility: PowerVisibility
    strain: int
    strain_cap: int
    granted_by: NodeRef | None
    item: NodeRef | None
    uses: int
    gained_epoch: int
    last_used_epoch: int | None
    locked: list[str]
    restrictions: list[PowerRestrictionView]
    triggers: list[PowerTriggerView]
    spans: list[PowerSpanView]


class PowerRegistryView(ApiModel):
    id: int
    polity: NodeRef
    holder: NodeRef
    licensed: bool
    conscripted: bool
    registered_epoch: int
    locked: list[str]


class GiftedAttitudeView(ApiModel):
    attitude: GiftedAttitude
    gifted_share: int
    registered_share: int
    updated_epoch: int
    locked: list[str]


class PowerChoice(ApiModel):
    id: int
    name: str


class PowersNodeView(ApiModel):
    node: NodeRef
    powers: list[PowerView]
    granted: list[PowerView]
    registry: list[PowerRegistryView]
    attitude: GiftedAttitudeView | None
    bloodline_rule: BloodlineRule | None
    sources: list[PowerChoice]
    systems: list[PowerChoice]
    grant_cost: int


class SourceCostView(ApiModel):
    id: int
    cost: PowerCost
    weight: int
    locked: list[str]


class SourceResistanceView(ApiModel):
    id: int
    resistance: ResistanceKind
    material: MaterialKind | None
    locked: list[str]


class SourceHazardView(ApiModel):
    id: int
    hazard: PowerHazard
    weight: int
    locked: list[str]


class SourceTideView(ApiModel):
    id: int
    cycle: TideCycle
    period: int
    amplitude: int
    phase: int
    locked: list[str]


class SourceInteractionView(ApiModel):
    id: int
    other_id: int
    other_name: str
    relation: SourceRelation
    strength: int
    locked: list[str]


class PowerSourceView(ApiModel):
    id: int
    name: str
    description: str
    scope: NodeRef | None
    drawn_from: SourceLocus
    renewal: SourceRenewal
    access: SourceAccess
    visibility: PowerVisibility
    stability: int
    built_in: MagicSource | None
    founded_epoch: int
    locked: list[str]
    costs: list[SourceCostView]
    resistances: list[SourceResistanceView]
    hazards: list[SourceHazardView]
    tides: list[SourceTideView]
    interactions: list[SourceInteractionView]


class DensityView(ApiModel):
    id: int
    source_id: int
    source_name: str
    density: int
    base_density: int
    renewal_pct: int
    last_drawn_epoch: int | None
    depleted: bool
    locked: list[str]


class SourceKnowledgeView(ApiModel):
    id: int
    source_id: int
    source_name: str
    level: int
    learned_epoch: int
    locked: list[str]


class SourceLawView(ApiModel):
    id: int
    source_id: int
    source_name: str
    level: SourceLawLevel
    locked: list[str]


class SourceStanceView(ApiModel):
    id: int
    source_id: int
    source_name: str
    stance: GiftedStance
    locked: list[str]


class SourcesNodeView(ApiModel):
    node: NodeRef
    sources: list[PowerSourceView]
    densities: list[DensityView]
    knowledge: list[SourceKnowledgeView]
    laws: list[SourceLawView]
    stances: list[SourceStanceView]
    power_stance: GiftedStance | None
    every_source: list[PowerChoice]


class SystemGrammarView(ApiModel):
    id: int
    technique: SpellTechnique | None
    form: SpellForm | None
    locked: list[str]


class SystemRestrictionView(ApiModel):
    id: int
    kind: RestrictionKind
    detail: str | None
    locked: list[str]


class SystemLinkView(ApiModel):
    id: int
    other_id: int
    other_name: str
    relation: SystemRelation
    locked: list[str]


class SystemSourceView(ApiModel):
    id: int
    source_id: int
    source_name: str
    locked: list[str]


class MagicSystemView(ApiModel):
    id: int
    name: str
    description: str
    structure: PowerStructure
    predictability: int
    prevalence: int
    cost_severity: int
    visibility: PowerVisibility
    access: SourceAccess
    learnability: Learnability
    founded_epoch: int
    locked: list[str]
    sources: list[SystemSourceView]
    links: list[SystemLinkView]
    grammar: list[SystemGrammarView]
    restrictions: list[SystemRestrictionView]


class MagicSystemsNodeView(ApiModel):
    node: NodeRef
    systems: list[MagicSystemView]
    every_system: list[PowerChoice]
    every_source: list[PowerChoice]


class TruthKeeperView(ApiModel):
    id: int
    keeper: NodeRef
    role: KeeperRole
    locked: list[str]


class SeekerView(ApiModel):
    id: int
    seeker: NodeRef
    aim: SeekerAim
    progress: int
    began_epoch: int
    locked: list[str]


class PublicKnowledgeView(ApiModel):
    id: int
    truth_id: int
    truth_title: str
    population: NodeRef
    know_pct: int
    believe_pct: int
    attitude: TruthAttitude
    revealed_epoch: int | None
    updated_epoch: int
    locked: list[str]


class TruthBreachView(ApiModel):
    id: int
    epoch: int
    cause: BreachCause
    witnesses: list[NodeRef]
    place: NodeRef | None
    spread: int
    response: KeeperResponse


class HiddenTruthView(ApiModel):
    id: int
    title: str
    description: str
    subject: NodeRef
    kind: HiddenTruthKind
    hidden_from: ConcealScope
    scope: NodeRef | None
    strength: int
    methods: list[str]
    sanity_cost: int
    revealed: bool
    founded_epoch: int
    tended_epoch: int
    locked: list[str]
    keepers: list[TruthKeeperView]
    seekers: list[SeekerView]
    knowledge: list[PublicKnowledgeView]
    breaches: list[TruthBreachView]


class TruthsNodeView(ApiModel):
    node: NodeRef
    about: list[HiddenTruthView]
    kept: list[HiddenTruthView]
    sought: list[HiddenTruthView]
    known_here: list[PublicKnowledgeView]
    methods: list[str]
