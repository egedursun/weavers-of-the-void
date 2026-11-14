from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.climes import CirculationBand, OscillationPhase
from aerona.domain.enums.mind import ValueAxis


class RegionWindView(ApiModel):
    region: NodeRef
    band: CirculationBand
    wind_from: int
    strength: int
    windward: bool
    shadow: int
    monsoon: int
    upwelling: bool
    read_epoch: int
    locked: list[str]


class MonsoonSeasonView(ApiModel):
    epoch: int
    strength: int
    failed: bool
    locked: list[str]


class OscillationView(ApiModel):
    phase: OscillationPhase
    period: int
    step: int
    strength: int
    locked: list[str]


class LaunchWindowView(ApiModel):
    from_world: NodeRef
    to_world: NodeRef
    synodic: int
    offset: int
    open: bool
    locked: list[str]


class RoadValueView(ApiModel):
    axis: ValueAxis
    value: int


class RoadMemberView(ApiModel):
    community: NodeRef
    share: int
    joined_epoch: int
    locked: list[str]


class RoadRouteChoice(ApiModel):
    id: int
    name: str


class CosmopolitanCultureView(ApiModel):
    id: int
    route: RoadRouteChoice | None
    name: str
    lingua_franca: NodeRef | None
    strength: int
    values: list[RoadValueView]
    formed_epoch: int
    members: list[RoadMemberView]
    locked: list[str]


class ClimesNodeView(ApiModel):
    node: NodeRef
    world: NodeRef | None
    region: NodeRef | None
    epoch: int
    winds: list[RegionWindView]
    monsoons: list[MonsoonSeasonView]
    oscillation: OscillationView | None
    windows: list[LaunchWindowView]
    cultures: list[CosmopolitanCultureView]
    routes: list[RoadRouteChoice]
