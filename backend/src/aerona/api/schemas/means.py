from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.honours import UnitHonourKind, VeteranGrant
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.means import ContainerKind, LockKind, NavigationAid, WaterLift, WritingMedium
from aerona.domain.enums.orders import (
    AllocationMode,
    Compensation,
    DistributionRule,
    HoardState,
    OrderLabour,
    OwnershipRegime,
    SavingForm,
    TouristSight,
    TransitionKind,
    TransitionStage,
)


class WritingCustomView(ApiModel):
    people: NodeRef
    medium: WritingMedium
    since_epoch: int
    locked: list[str]


class WrittenWorkView(ApiModel):
    work: NodeRef
    medium: WritingMedium
    condition: int
    copies: int
    written_epoch: int
    locked: list[str]


class VaultView(ApiModel):
    holder: NodeRef
    lock: LockKind | None
    lock_quality: int
    sealed: bool
    guards: int
    traps: bool
    thwarted: int
    since_epoch: int
    locked: list[str]


class WaterLiftView(ApiModel):
    device: WaterLift
    count: int
    capacity: int
    since_epoch: int
    locked: list[str]


class NavigationKitView(ApiModel):
    aid: NavigationAid
    quality: int
    works: bool
    since_epoch: int
    locked: list[str]


class ContainerStockView(ApiModel):
    kind: ContainerKind
    count: int
    broken: int
    capacity: int
    sealed: bool
    locked: list[str]


class BuildingView(ApiModel):
    material: MaterialKind | None
    water_resistance: int
    needs: Technique | None
    can_repair: bool
    weathering_pct: int


class MeansNodeView(ApiModel):
    node: NodeRef
    town: NodeRef | None
    people: NodeRef | None
    custom: WritingCustomView | None
    works: list[WrittenWorkView]
    vaults: list[VaultView]
    lifts: list[WaterLiftView]
    kits: list[NavigationKitView]
    accuracy: int
    containers: list[ContainerStockView]
    building: BuildingView | None


class SavingView(ApiModel):
    household_id: int
    household: str
    share_pct: int
    form: SavingForm
    saved: int
    updated_epoch: int
    locked: list[str]


class HoardView(ApiModel):
    id: int
    holder: NodeRef | None
    place: NodeRef
    amount: int
    state: HoardState
    hidden_epoch: int
    found_by: NodeRef | None
    found_epoch: int | None
    locked: list[str]


class CoinView(ApiModel):
    id: int
    name: str


class RateView(ApiModel):
    id: int
    base: CoinView
    quote: CoinView
    market: NodeRef | None
    rate: int
    spread_pct: int
    changer: NodeRef | None
    convertible: bool
    volume: int
    updated_epoch: int
    locked: list[str]


class BillView(ApiModel):
    id: int
    drawer: NodeRef
    payee: NodeRef
    from_market: NodeRef
    to_market: NodeRef
    amount: int
    issued_epoch: int
    settled: bool
    locked: list[str]


class OrderView(ApiModel):
    id: int
    sector: CommodityKind | None
    ownership: OwnershipRegime
    allocation: AllocationMode
    labour: OrderLabour
    distribution: DistributionRule
    planning_capacity: int
    kind_id: int | None
    kind_name: str | None
    since_epoch: int
    locked: list[str]


class OrderKindView(ApiModel):
    id: int
    name: str
    ownership: OwnershipRegime
    allocation: AllocationMode
    labour: OrderLabour
    distribution: DistributionRule
    built_in: bool
    locked: list[str]


class AxesView(ApiModel):
    ownership: OwnershipRegime | None
    allocation: AllocationMode | None
    labour: OrderLabour | None
    distribution: DistributionRule | None


class OrderTransitionView(ApiModel):
    id: int
    sector: CommodityKind | None
    kind: TransitionKind
    stage: TransitionStage
    compensation: Compensation
    resistance: int
    transferred: int
    from_axes: AxesView
    to_axes: AxesView
    started_epoch: int
    ended_epoch: int | None
    locked: list[str]


class PuttingOutView(ApiModel):
    id: int
    merchant: NodeRef
    village: NodeRef
    raw: CommodityKind
    product: CommodityKind
    volume: int
    active: bool
    since_epoch: int
    locked: list[str]


class ChainView(ApiModel):
    holder: NodeRef
    town: NodeRef
    product: CommodityKind
    share_pct: int
    since_epoch: int
    locked: list[str]


class TouristFlowView(ApiModel):
    id: int
    origin: NodeRef
    sight_node: NodeRef
    sight: TouristSight
    visitors: int
    income: int
    epoch: int
    locked: list[str]


class HouseholdChoice(ApiModel):
    id: int
    name: str


class OrdersNodeView(ApiModel):
    node: NodeRef
    realm: NodeRef | None
    orders: list[OrderView]
    kinds: list[OrderKindView]
    transitions: list[OrderTransitionView]
    households: list[HouseholdChoice]
    savings: list[SavingView]
    hoards: list[HoardView]
    coins: list[CoinView]
    rates: list[RateView]
    bills: list[BillView]
    putting_out: list[PuttingOutView]
    chains: list[ChainView]
    flows: list[TouristFlowView]


class UnitHonourView(ApiModel):
    id: int
    kind: UnitHonourKind
    note: str
    epoch: int
    locked: list[str]


class NamedUnitView(ApiModel):
    id: int
    unit_id: int | None
    owner: NodeRef | None
    name: str
    nickname: str | None
    raised_from: NodeRef | None
    esprit: int
    battles: int
    formed_epoch: int
    disbanded_epoch: int | None
    honours: list[UnitHonourView]
    locked: list[str]


class ArmyUnitChoice(ApiModel):
    id: int
    label: str
    count: int


class VeteranGrantView(ApiModel):
    id: int
    polity: NodeRef
    kind: VeteranGrant
    veterans: int
    settlement: NodeRef | None
    war: NodeRef | None
    epoch: int
    locked: list[str]


class HonoursNodeView(ApiModel):
    node: NodeRef
    realm: NodeRef | None
    units: list[NamedUnitView]
    choices: list[ArmyUnitChoice]
    grants: list[VeteranGrantView]
