from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.creator import (
    ChosenFavour,
    CovenantDuty,
    CovenantState,
    CreatorHeresy,
    CreatorNature,
    CreatorPromise,
    CreatorSignKind,
    CreatorStance,
)
from aerona.domain.enums.domain import Domain


class CreatorStandingView(ApiModel):
    awe: int
    love: int
    dread: int
    gratitude: int
    resentment: int
    ignorance: int
    stance: CreatorStance
    heresy: CreatorHeresy
    updated_epoch: int
    locked: list[str]


class CovenantView(ApiModel):
    id: int
    duty: CovenantDuty
    promise: CreatorPromise
    seal_sign: CreatorSignKind
    state: CovenantState
    since_epoch: int
    until_epoch: int | None
    breaches: int
    locked: list[str]


class ChosenView(ApiModel):
    favour: ChosenFavour
    since_epoch: int
    locked: list[str]


class DepictionView(ApiModel):
    name: str
    nature: CreatorNature
    aspect: Domain | None
    updated_epoch: int
    locked: list[str]


class CreatorBondsView(ApiModel):
    node: NodeRef
    is_people: bool
    standing: CreatorStandingView | None
    depiction: DepictionView | None
    covenants: list[CovenantView]
    chosen: ChosenView | None
    far_epochs: int | None
