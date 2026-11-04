from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.body import Capacity
from aerona.domain.enums.entity import MortalRole
from aerona.domain.enums.mind import (
    MemoryKind,
    NeedKind,
    OpinionComponent,
    PressureKind,
    SkillFamily,
    SkillKind,
    SkillSource,
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


class NeedView(ApiModel):
    need: NeedKind
    label: str
    value: int


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
