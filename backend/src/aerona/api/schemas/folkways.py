from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.folkways import (
    AccusationOutcome,
    BiasedDecision,
    CharmPower,
    DecisionBias,
    ImpuritySource,
    LuckReach,
    LuckSign,
    MishapAttribution,
    MishapKind,
    MishapResponse,
    Nutrient,
    Purification,
    PurityState,
)


class DietView(ApiModel):
    staple: int
    protein: int
    fat: int
    fresh: int
    mineral: int
    preserved: int
    special: int
    energy: int
    updated_epoch: int
    locked: list[str]


class NutritionView(ApiModel):
    energy: int
    balance: int
    score: int
    deficiency: Nutrient | None
    childhood: int | None
    grown: bool
    updated_epoch: int
    locked: list[str]


class NeedView(ApiModel):
    nutrient: Nutrient
    weight: int
    locked: list[str]


class DecisionBiasView(ApiModel):
    bias: DecisionBias
    weight: int
    last_decision: BiasedDecision | None
    last_shift: int
    last_epoch: int | None
    locked: list[str]


class PurityRankView(ApiModel):
    id: int
    name: str
    standing: int
    professions: list[str]
    endogamous: bool
    commensal: bool
    locked: list[str]


class PurityView(ApiModel):
    state: PurityState
    source: ImpuritySource | None
    since_epoch: int
    until_epoch: int | None
    rank_id: int | None
    locked: list[str]


class SourceView(ApiModel):
    source: ImpuritySource
    weight: int
    lasts: int
    locked: list[str]


class MethodView(ApiModel):
    method: Purification
    epochs: int
    cost: int
    success: int
    locked: list[str]


class MishapView(ApiModel):
    id: int
    town: NodeRef
    victim: NodeRef | None
    cause: NodeRef | None
    kind: MishapKind
    true_cause: str
    explained: bool
    attribution: MishapAttribution | None
    response: MishapResponse | None
    severity: int
    died: bool
    witnesses: list[NodeRef]
    epoch: int
    locked: list[str]


class LuckBeliefView(ApiModel):
    id: int
    sign: LuckSign
    reach: LuckReach
    lucky: bool
    name: str
    locked: list[str]


class CharmView(ApiModel):
    item: NodeRef
    power: CharmPower
    real: bool
    strength: int
    locked: list[str]


class AccusationView(ApiModel):
    id: int
    town: NodeRef | None
    accuser: NodeRef | None
    accused: NodeRef
    mishap_id: int | None
    hunt_id: int | None
    case_id: int | None
    outcome: AccusationOutcome
    guilty_in_truth: bool
    opened_epoch: int
    closed_epoch: int | None
    locked: list[str]


class HuntView(ApiModel):
    id: int
    fervour: int
    accused: int
    killed: int
    started_epoch: int
    ended_epoch: int | None
    locked: list[str]


class FolkwaysNodeView(ApiModel):
    node: NodeRef
    people: NodeRef | None
    diet: DietView | None
    nutrition: NutritionView | None
    needs: list[NeedView]
    biases: list[DecisionBiasView]
    purity: PurityView | None
    ranks: list[PurityRankView]
    sources: list[SourceView]
    methods: list[MethodView]
    mishaps: list[MishapView]
    beliefs: list[LuckBeliefView]
    charms: list[CharmView]
    accusations: list[AccusationView]
    hunts: list[HuntView]
