from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.mind import RelationComponent
from aerona.domain.enums.regime import SelectorateKind
from aerona.domain.enums.travel import EncounterEffect, RouteEnvironment


class RelationPartView(ApiModel):
    component: RelationComponent
    value: int
    updated_epoch: int
    locked: list[str]


class RelationPartsView(ApiModel):
    parts: list[RelationPartView]


class ConstitutionView(ApiModel):
    ideology: NodeRef | None
    selectorate: SelectorateKind
    offices: int
    rights: int
    written_epoch: int
    locked: list[str]


class ConstitutionOfView(ApiModel):
    is_realm: bool
    constitution: ConstitutionView | None


class JourneyEncounterView(ApiModel):
    id: int
    world: NodeRef | None
    environment: RouteEnvironment
    effect: EncounterEffect
    name: str | None
    weight: int
    loss_pct: int
    locked: list[str]
