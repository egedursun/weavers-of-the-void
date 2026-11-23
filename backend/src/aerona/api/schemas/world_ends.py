from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.world import WorldType
from aerona.domain.enums.world_end import WorldEnd, WorldEndCause


class WorldEndNodeView(ApiModel):
    node: NodeRef
    world: NodeRef | None
    world_type: WorldType | None
    state: WorldEnd | None
    cause: WorldEndCause | None
    epoch: int | None
    former_type: WorldType | None
    new_type: WorldType | None
    source: NodeRef | None = None
    lives_ended: int
    homeless: int
    anchors_lost: int
    routes_closed: int
    locked: list[str]
    end_cost: int
    absent_reason: str | None
