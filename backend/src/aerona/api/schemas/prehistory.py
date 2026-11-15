from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.prehistory import DeepTimeState, PrehistoryKind, PrehistorySource, PrehistoryState
from aerona.domain.enums.world import WorldType


class PrehistoryHappeningView(ApiModel):
    id: int
    round: int
    magnitude: int
    source: PrehistorySource
    text: str | None
    subject: NodeRef | None
    source_world: NodeRef | None
    mirrored: bool
    locked: list[str]


class PrehistoryNodeView(ApiModel):
    node: NodeRef
    world: NodeRef | None
    world_type: WorldType | None
    kind_of_world: PrehistoryKind | None
    kind: PrehistoryKind | None
    state: PrehistoryState | None
    source: PrehistorySource | None
    epochs: int
    resolution: int
    rounds_done: int
    birth_epoch: int | None
    seconds: int
    slow_rounds: int
    source_world: NodeRef | None
    locked: list[str]
    happenings: list[PrehistoryHappeningView]
    lore_free: bool
    default_epochs: int
    default_resolution: int
    epochs_max: int
    resolution_max: int
    seed_cost: int
    absent_reason: str | None


class DeepTimeHappeningView(ApiModel):
    id: int
    epoch: int
    magnitude: int
    text: str | None
    locked: list[str]


class DeepTimeRunView(ApiModel):
    id: int
    epochs: int
    ran: int
    from_epoch: int
    to_epoch: int
    state: DeepTimeState
    sons_simulated: int
    locked: list[str]
    happenings: list[DeepTimeHappeningView]


class DeepTimeView(ApiModel):
    runs: list[DeepTimeRunView]
    max_epochs: int
    cost_per_epoch: int
