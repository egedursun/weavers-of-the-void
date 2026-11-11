from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.urban import (
    ConvoyStatus,
    CrimeStance,
    HousingLevel,
    MarketPlay,
    Morphology,
    OrderLaw,
    Preservation,
    RacketKind,
    TransportKind,
    TribunalVerdict,
    UrbanService,
)


class CoverageView(ApiModel):
    service: UrbanService
    coverage: int
    epoch: int
    locked: list[str]


class TurfView(ApiModel):
    district_id: int
    district_kind: DistrictKind | None
    town: NodeRef | None
    faction: NodeRef | None
    strength: int
    since_epoch: int
    locked: list[str]


class DistrictUrbanView(ApiModel):
    id: int
    kind: DistrictKind
    level: int
    housing: HousingLevel
    desirability: int
    land_value: int
    services: list[CoverageView]
    turf: list[TurfView]
    locked: list[str]


class TownUrbanView(ApiModel):
    morphology: Morphology
    homeless: int
    locked: list[str]


class DistrictChoice(ApiModel):
    id: int
    kind: DistrictKind
    level: int


class PlacementView(ApiModel):
    district_id: int | None
    choices: list[DistrictChoice]


class RacketView(ApiModel):
    faction: NodeRef | None
    settlement: NodeRef | None
    racket: RacketKind
    income: int
    since_epoch: int
    locked: list[str]


class PayrollView(ApiModel):
    faction: NodeRef | None
    official: NodeRef | None
    bribe: int
    since_epoch: int
    locked: list[str]


class CrimeStanceView(ApiModel):
    polity: NodeRef | None
    faction: NodeRef | None
    stance: CrimeStance
    strength: int
    since_epoch: int
    locked: list[str]


class OrderLawView(ApiModel):
    law: OrderLaw
    strength: int
    locked: list[str]


class TribunalView(ApiModel):
    id: int
    order: NodeRef | None
    accused: NodeRef | None
    law: OrderLaw
    verdict: TribunalVerdict
    fine: int
    epoch: int


class TradingPostView(ApiModel):
    structure: NodeRef | None
    owner: NodeRef | None
    host: NodeRef | None
    informants: int
    goods: int
    since_epoch: int
    locked: list[str]


class ConvoyView(ApiModel):
    id: int
    owner: NodeRef | None
    route: NodeRef | None
    cargo: dict[str, int]
    preservation: Preservation
    animals: int
    vehicles: int
    guards: int
    passengers: dict[str, int]
    season: int
    status: ConvoyStatus
    region: NodeRef | None
    capacity: int
    departed_epoch: int
    arrived_epoch: int | None
    locked: list[str]


class FleetView(ApiModel):
    owner: NodeRef | None
    kind: TransportKind
    count: int
    age: int
    condition: int
    locked: list[str]


class MarketPlayView(ApiModel):
    holder: NodeRef | None
    settlement: NodeRef | None
    commodity: CommodityKind
    play: MarketPlay
    strength: int
    since_epoch: int
    until_epoch: int | None
    locked: list[str]


class NodeUrbanView(ApiModel):
    node: NodeRef
    town: TownUrbanView | None
    districts: list[DistrictUrbanView]
    placement: PlacementView | None
    turf: list[TurfView]
    rackets: list[RacketView]
    payroll: list[PayrollView]
    stances: list[CrimeStanceView]
    laws: list[OrderLawView]
    tribunals: list[TribunalView]
    posts: list[TradingPostView]
    convoys: list[ConvoyView]
    fleets: list[FleetView]
    plays: list[MarketPlayView]
