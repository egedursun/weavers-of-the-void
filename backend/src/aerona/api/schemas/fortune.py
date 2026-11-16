from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.folkways import MishapKind
from aerona.domain.enums.fortune import FortuneLaw, FortuneSourceKind


class FortuneSourceView(ApiModel):
    id: int
    kind: FortuneSourceKind
    strength: int
    giver: NodeRef | None
    until_epoch: int | None
    since_epoch: int
    locked: list[str]


class FortuneMishapView(ApiModel):
    id: int
    kind: MishapKind
    severity: int
    died: bool
    explained: bool
    epoch: int


class CohortMishapView(ApiModel):
    epoch: int
    injured: int
    dead: int
    rate_pct: int


class FortuneNodeView(ApiModel):
    node: NodeRef
    fortune: int
    streak: int
    held_values: list[str]
    law: FortuneLaw
    world_id: int | None
    sources: list[FortuneSourceView]
    mishaps: list[FortuneMishapView]
    cohort: list[CohortMishapView]
