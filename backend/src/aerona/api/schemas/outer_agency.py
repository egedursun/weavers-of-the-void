from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.outer import IncursionStage, OuterFate, OuterGoal, OuterPlanState, OuterPrice, OuterRelation, OuterSealKind


class OuterPlanView(ApiModel):
    id: int
    goal: OuterGoal
    stage: int
    stages: int
    progress: int
    target: NodeRef | None
    state: OuterPlanState
    started_epoch: int
    sign_epoch: int | None
    locked: list[str]


class OuterHeraldView(ApiModel):
    herald: NodeRef
    zeal: int
    bound_epoch: int
    locked: list[str]


class OuterIncursionView(ApiModel):
    id: int
    rift_id: int | None
    region: NodeRef | None
    stage: IncursionStage
    strength: int
    started_epoch: int
    ended_epoch: int | None
    locked: list[str]


class OuterPactView(ApiModel):
    id: int
    holder: NodeRef
    price: OuterPrice
    paid: bool
    power_id: int | None
    struck_epoch: int
    locked: list[str]


class OuterRelationView(ApiModel):
    other: NodeRef
    relation: OuterRelation
    since_epoch: int
    locked: list[str]


class OuterSealView(ApiModel):
    id: int
    kind: OuterSealKind
    strength: int
    sealer: NodeRef | None
    sealed_epoch: int
    broken_epoch: int | None
    locked: list[str]


class OuterAgencyView(ApiModel):
    being: NodeRef
    fate: OuterFate
    unfed_epochs: int
    starve_epochs: int
    plans: list[OuterPlanView]
    heralds: list[OuterHeraldView]
    incursions: list[OuterIncursionView]
    pacts: list[OuterPactView]
    relations: list[OuterRelationView]
    seals: list[OuterSealView]
