from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.kinds import KindConcept, KindSpread, KindStance


class KindCategoryInfo(ApiModel):
    key: str
    label: str


class KindPropertyInfo(ApiModel):
    column: str
    label: str
    hint: str
    low: int
    high: int
    options: list[KindCategoryInfo]


class KindConceptInfo(ApiModel):
    concept: KindConcept
    label: str
    plural: str
    hint: str
    categories: list[KindCategoryInfo]
    properties: list[KindPropertyInfo]


class KindValue(ApiModel):
    column: str
    value: int
    option: str | None
    option_label: str | None


class AuthoredKindRecord(ApiModel):
    id: int
    concept: KindConcept
    name: str
    description: str | None
    category: str
    category_label: str
    world: NodeRef | None
    origin: NodeRef | None
    derived_from_id: int | None
    derived_from_name: str | None
    built_in: bool
    retired: bool
    created_epoch: int
    locked: list[str]
    values: list[KindValue]
    holders: list[NodeRef]


class KindHoldingView(ApiModel):
    id: int
    concept: KindConcept
    kind_id: int
    kind_name: str
    category_label: str
    stance: KindStance
    strength: int
    spread: KindSpread
    since_epoch: int
    locked: list[str]


class WaysOfLifeView(ApiModel):
    node: NodeRef
    holdings: list[KindHoldingView]
    made: list[AuthoredKindRecord]
