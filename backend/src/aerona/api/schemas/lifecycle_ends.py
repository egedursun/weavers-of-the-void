from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.lifecycle_end import LifecycleCause, LifecycleKind, LifecycleState


class LifecycleNodeView(ApiModel):
    node: NodeRef
    kind: LifecycleKind | None
    state: LifecycleState | None
    cause: LifecycleCause | None
    idle_epochs: int
    grace_epochs: int
    since_epoch: int | None
    holders: int
    texts: int
    seeded: bool
    locked: list[str]
    destroy_cost: int
    absent_reason: str | None
