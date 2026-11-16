from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.foreign_god import PantheonStructure, PantheonTie


class PantheonStructureView(ApiModel):
    world: NodeRef
    structure: PantheonStructure
    head: NodeRef | None
    since_epoch: int
    locked: list[str]


class PantheonTieView(ApiModel):
    god: NodeRef
    other: NodeRef
    tie: PantheonTie
    since_epoch: int
    locked: list[str]


class SyncretismView(ApiModel):
    id: int
    foreign_god: NodeRef
    son: NodeRef
    people: NodeRef
    dominant: NodeRef | None
    since_epoch: int
    locked: list[str]


class PantheonOfView(ApiModel):
    node: NodeRef
    is_god: bool
    pantheon: PantheonStructureView | None
    ties: list[PantheonTieView]
    syncretisms: list[SyncretismView]
