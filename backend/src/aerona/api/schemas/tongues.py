from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.tongues import (
    LanguageModality,
    LanguagePolicy,
    LanguageStage,
    MorphologyType,
    NumberSystem,
    NumeralBase,
    ScriptChangeCause,
    SenseShift,
    SoundChangeCause,
    SoundChangeKind,
    SoundEnvironment,
    WordOrder,
)


class SoundChangeView(ApiModel):
    id: int
    kind: SoundChangeKind
    source: str
    target: str
    environment: SoundEnvironment
    cause: SoundChangeCause
    position: int
    epoch: int
    locked: list[str]


class TongueGrammarView(ApiModel):
    word_order: WordOrder
    morphology: MorphologyType
    cases: int
    noun_classes: int
    evidentiality: bool
    honorific_levels: int
    number_system: NumberSystem
    updated_epoch: int
    locked: list[str]


class ScriptView(ApiModel):
    id: int
    name: str
    system: WritingSystem
    parent_script_id: int | None
    origin_language: NodeRef | None
    signs: int
    cause: ScriptChangeCause
    epoch: int
    locked: list[str]


class DecipherView(ApiModel):
    progress: int
    corpus: int
    bilingual: bool
    errors: int
    scholar: NodeRef | None
    started_epoch: int
    updated_epoch: int
    locked: list[str]


class PolicyView(ApiModel):
    holder: NodeRef | None
    language: NodeRef | None
    policy: LanguagePolicy
    strength: int
    since_epoch: int
    locked: list[str]


class MeaningShiftView(ApiModel):
    id: int
    lexeme_id: int
    word: str
    shift: SenseShift
    old_meaning: str
    new_meaning: str
    absorbed_word: str | None
    cause: NodeRef | None
    epoch: int


class DivineTongueView(ApiModel):
    god: NodeRef | None
    language: NodeRef | None
    since_epoch: int
    locked: list[str]


class TongueMechanicsView(ApiModel):
    modality: LanguageModality
    stage: LanguageStage
    numeral_base: NumeralBase
    ancestor: NodeRef | None
    writing_system: WritingSystem | None
    script: ScriptView | None
    lineage: list[ScriptView]
    grammar: TongueGrammarView | None
    changes: list[SoundChangeView]
    decipher: DecipherView | None
    policies: list[PolicyView]
    shifts: list[MeaningShiftView]
    sacred_to: DivineTongueView | None


class NodeTonguesView(ApiModel):
    node: NodeRef
    language: TongueMechanicsView | None
    held_policies: list[PolicyView]
    divine_tongue: DivineTongueView | None
    known_divine: list[NodeRef]
