from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.body import Capacity
from aerona.domain.enums.entity import MortalRole
from aerona.domain.enums.mind import (
    ActKind,
    Attribute,
    DreamKind,
    DreamReading,
    Emotion,
    EthicalStance,
    Facet,
    FacetGroup,
    GriefStage,
    HonourModel,
    IdeaKind,
    IdeaSource,
    IdeaState,
    MemoryKind,
    MoodState,
    NeedGroup,
    NeedKind,
    OpinionComponent,
    PreferenceKind,
    PressureKind,
    SkillFamily,
    SkillKind,
    SkillSource,
    ThoughtKind,
    TraitEffect,
    TraitKind,
    TraitSource,
    ValueAxis,
    ValueHolder,
)


class ValueView(ApiModel):
    axis: ValueAxis
    value: int
    low_label: str
    high_label: str
    reference: int | None


class TraitEffectView(ApiModel):
    effect: TraitEffect
    value: int


class TraitCapacityView(ApiModel):
    capacity: Capacity
    value: int


class TraitView(ApiModel):
    trait: TraitKind
    label: str
    source: TraitSource
    epoch: int
    source_node: NodeRef | None
    opposite: TraitKind | None
    heritable: bool
    effects: list[TraitEffectView]
    capacities: list[TraitCapacityView]
    variant_id: int | None = None


class SkillView(ApiModel):
    id: int
    skill: SkillKind
    label: str
    family: SkillFamily
    capacity: Capacity
    level: int
    effective: int
    peak: int
    xp: int
    next_level_xp: int
    last_used_epoch: int
    rusting: bool
    source: SkillSource
    subject: NodeRef | None = None
    variant_id: int | None = None


class NeedView(ApiModel):
    need: NeedKind
    label: str
    value: int
    group: NeedGroup
    importance: int


class PressureView(ApiModel):
    pressure: PressureKind
    label: str
    value: int


class MemoryView(ApiModel):
    id: int
    subject: NodeRef | None
    kind: MemoryKind
    label: str
    magnitude: int
    strength: int
    decay_pct: int
    epoch: int
    note: str | None
    inherited_from: NodeRef | None


class OpinionTermView(ApiModel):
    key: str
    value: int


class OpinionComponentView(ApiModel):
    component: OpinionComponent
    value: int


class OpinionMemoryView(ApiModel):
    id: int
    kind: MemoryKind
    label: str
    epoch: int
    strength: int
    weight_pct: int
    contribution: int
    note: str | None


class OpinionView(ApiModel):
    holder: NodeRef | None
    subject: NodeRef | None
    value: int
    alignment: int
    components: list[OpinionComponentView]
    terms: list[OpinionTermView]
    memories: list[OpinionMemoryView]


class CareerView(ApiModel):
    role: MortalRole | None
    ended_epoch: int | None
    fixed: bool


class MindView(ApiModel):
    node_id: int
    name: str
    holder: ValueHolder
    locked: list[str]
    lockable: list[str]
    borrowed_from: NodeRef | None
    reference: NodeRef | None
    values: list[ValueView]
    traits: list[TraitView]
    skills: list[SkillView]
    needs: list[NeedView]
    pressures: list[PressureView]
    memories: list[MemoryView]
    opinions: list[OpinionView]
    career: CareerView | None
    max_traits: int


class AttributeView(ApiModel):
    attribute: Attribute
    label: str
    physical: bool
    value: int
    effective: int
    governs: list[SkillKind]


class FacetView(ApiModel):
    facet: Facet
    label: str
    group: FacetGroup
    value: int
    mean: int
    high_trait: TraitKind | None
    low_trait: TraitKind | None


class BeliefShiftView(ApiModel):
    axis: ValueAxis
    label: str
    value: int


class AttributeShiftView(ApiModel):
    attribute: Attribute
    label: str
    value: int


class FacetShiftView(ApiModel):
    facet: Facet
    label: str
    value: int


class IdeaSpecView(ApiModel):
    idea: IdeaKind
    label: str
    beliefs: list[BeliefShiftView]
    gains: list[AttributeShiftView]
    costs: list[AttributeShiftView]
    facets: list[FacetShiftView]
    distraction: int


class IdeaView(ApiModel):
    id: int
    idea: IdeaKind
    label: str
    source: IdeaSource
    source_node: NodeRef | None
    progress: int
    state: IdeaState
    started_epoch: int
    finished_epoch: int | None
    fit: int


class SummaryView(ApiModel):
    name: str
    value: int


class MindSplitView(ApiModel):
    node_id: int
    name: str
    has_attributes: bool
    has_facets: bool
    turns_ideas: bool
    locked: list[str]
    lockable: list[str]
    attributes: list[AttributeView]
    summaries: list[SummaryView]
    facets: list[FacetView]
    ideas: list[IdeaView]
    catalogue: list[IdeaSpecView]
    trait_threshold: int
    idea_slots: int


class ThoughtView(ApiModel):
    id: int
    kind: ThoughtKind
    label: str
    emotion: Emotion
    emotion_label: str
    valence: int
    intensity: int
    strength: int
    epoch: int
    decay_pct: int
    subject: NodeRef | None
    formative: bool


class EmotionTotalView(ApiModel):
    emotion: Emotion
    label: str
    valence: int
    strength: int


class FormativeView(ApiModel):
    id: int
    label: str
    magnitude: int
    epoch: int
    subject: NodeRef | None


class GriefView(ApiModel):
    id: int
    deceased: NodeRef | None
    stage: GriefStage
    strength: int
    started_epoch: int
    stage_epoch: int
    length_epochs: int


class DreamLogView(ApiModel):
    id: int
    kind: DreamKind
    label: str
    epoch: int
    intensity: int
    content: list[NodeRef]
    sender: NodeRef | None
    partner: NodeRef | None
    world: NodeRef | None
    reading: DreamReading
    reading_label: str
    reader: NodeRef | None
    reading_true: bool | None
    recurring: bool


class ThoughtKindView(ApiModel):
    kind: ThoughtKind
    label: str
    emotion: Emotion


class EmotionKindView(ApiModel):
    emotion: Emotion
    label: str
    valence: int


class LabelView(ApiModel):
    key: str
    label: str


class FeelingsView(ApiModel):
    node_id: int
    name: str
    applies: bool
    locked: list[str]
    lockable: list[str]
    mood: MoodState | None
    mood_score: int
    mood_held: bool
    thoughts: list[ThoughtView]
    emotions: list[EmotionTotalView]
    formative: list[FormativeView]
    griefs: list[GriefView]
    dreams: list[DreamLogView]
    thought_kinds: list[ThoughtKindView]
    emotion_kinds: list[EmotionKindView]
    dream_kinds: list[LabelView]
    readings: list[LabelView]
    long_term_threshold: int


class PreferenceView(ApiModel):
    id: int
    kind: PreferenceKind
    kind_label: str
    target: str
    target_label: str
    target_node: NodeRef | None
    strength: int
    held: bool


class PreferenceKindView(ApiModel):
    kind: PreferenceKind
    label: str
    targets: list[str]
    from_records: bool


class EthicView(ApiModel):
    act: ActKind
    label: str
    stance: EthicalStance
    stance_label: str
    reading: int
    since_epoch: int
    held: bool


class CultureMindView(ApiModel):
    node_id: int
    name: str
    has_preferences: bool
    has_ethics: bool
    ethics_holder: NodeRef | None
    ethics_own: bool
    preferences: list[PreferenceView]
    totem: NodeRef | None
    ethics: list[EthicView]
    honour_model: HonourModel | None
    honour_label: str | None
    honour_held: bool
    preference_kinds: list[PreferenceKindView]
    stances: list[LabelView]
    honour_models: list[LabelView]
