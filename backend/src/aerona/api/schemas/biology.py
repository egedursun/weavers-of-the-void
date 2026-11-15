from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.biology import BiologyVariant
from aerona.domain.enums.folkways import DecisionBias


class BiologyEffectsView(ApiModel):
    food_need_pct: int
    fertility_pct: int
    death_pct: int
    disease_pct: int
    morale_loss_pct: int
    fire_harm_pct: int
    storm_harm_pct: int
    breathes: bool
    drinks: bool
    ages: bool


class BiologyLeaningView(ApiModel):
    bias: DecisionBias
    shift: int
    damped: bool


class BiologyNodeView(ApiModel):
    node: NodeRef
    holder: NodeRef | None
    variants: list[BiologyVariant]
    body_variants: list[BiologyVariant]
    effects: BiologyEffectsView | None
    derived: BiologyEffectsView | None
    leanings: list[BiologyLeaningView]
    seeded: bool
    updated_epoch: int | None
    locked: list[str]
    absent_reason: str | None
