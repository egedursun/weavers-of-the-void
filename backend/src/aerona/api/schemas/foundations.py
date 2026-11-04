from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.war import WarEnding, WarStatus


class GoldenAgeView(ApiModel):
    world_id: int
    active: bool
    since_epoch: int | None
    epochs: int
    prosperity_gain: int
    decadence: int
    held: bool
    communities: int
    golden_communities: int
    deepening_epochs: int
    deepening_steps: int
    decadence_epochs: int


class IncitedWarView(ApiModel):
    war_id: int
    event: NodeRef | None
    status: WarStatus
    ending: WarEnding | None
    started_epoch: int
    ended_epoch: int | None
    battles: int
    held: bool


class AnchorageView(ApiModel):
    son_id: int
    anchor: NodeRef | None
    anchor_alive: bool
    anchor_held: bool
    shrines: list[NodeRef]
    incited: list[IncitedWarView]


class DedicationView(ApiModel):
    structure_id: int
    son: NodeRef | None
    held: bool
    anchors_son: bool
