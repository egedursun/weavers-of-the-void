from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.law_grammar import LawCondition, LawExceptionKind, LawOperator, LawTarget
from aerona.domain.enums.society import NaturalLaw


class LawExceptionView(ApiModel):
    id: int
    kind: LawExceptionKind
    node: NodeRef | None
    entity_type: EntityType | None
    locked: list[str]


class LawTheoryView(ApiModel):
    id: int
    holder: NodeRef
    believed_operator: LawOperator
    believed_value: int
    confidence: int
    adapted_epochs: int
    gap: int
    updated_epoch: int
    locked: list[str]


class LawTargetFields(ApiModel):
    target: LawTarget
    keys: list[str]


class LawGrammarView(ApiModel):
    law: NodeRef
    preset: NaturalLaw
    target: LawTarget | None
    operator: LawOperator | None
    key: str | None
    value: int
    condition: LawCondition
    until_epoch: int | None
    suspended: bool
    contested: bool
    written: str
    exceptions: list[LawExceptionView]
    theories: list[LawTheoryView]
    targets: list[LawTargetFields]
    locked: list[str]
