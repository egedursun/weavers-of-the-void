from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.cosmography import RiftWork
from aerona.domain.enums.intrigue import BeliefSource


class SourceTrustView(ApiModel):
    source: BeliefSource
    trust: int
    right: int
    wrong: int
    updated_epoch: int
    locked: list[str]


class SourceTrustOfView(ApiModel):
    node: NodeRef
    sources: list[SourceTrustView]


class RiftControlView(ApiModel):
    rift_id: int
    claimant: NodeRef | None
    work: RiftWork
    toll: int
    adapted: int
    claimed_epoch: int | None
    locked: list[str]


class RiftControlsView(ApiModel):
    controls: list[RiftControlView]
