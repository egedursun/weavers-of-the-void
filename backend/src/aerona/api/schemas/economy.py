from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.economy import (
    CommodityFamily,
    CommodityKind,
    LoanStatus,
    MaterialFamily,
    MaterialOrigin,
    TradeLoss,
    TradeMode,
    TradeRouteStatus,
    WorkshopKind,
)
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import KnowledgeBranch


class MaterialView(ApiModel):
    kind: MaterialKind | None
    world_material_id: int | None
    label: str
    family: MaterialFamily
    origin: MaterialOrigin
    edited: bool
    hardness: int
    toughness: int
    weight: int
    edge: int
    conductivity: int
    sanctity: int
    corruption: int
    rarity: int
    base_value: int
    decay: int
    branch: KnowledgeBranch | None
    level: int
    gate: KnowledgeBranch | None
    description: str | None = None
    deposit_id: int | None = None


class CommodityView(ApiModel):
    kind: CommodityKind
    label: str
    family: CommodityFamily
    base_price: int
    nourishment: int
    strategic: bool
    per_1000: int


class MaterialsView(ApiModel):
    world_id: int
    materials: list[MaterialView]
    commodities: list[CommodityView]


class StockLotView(ApiModel):
    id: int
    commodity: CommodityKind
    material: MaterialKind | None
    world_material_id: int | None
    label: str
    quantity: int
    quality: int


class WorkshopView(ApiModel):
    kind: WorkshopKind
    label: str
    level: int
    fleet: int
    idle_epochs: int
    built_epoch: int
    structure_id: int | None


class ChainStepView(ApiModel):
    key: str
    label: str
    workshop: WorkshopKind | None
    inputs: dict[str, int]
    output: CommodityKind
    output_qty: int
    made: int
    quality: int
    material: MaterialKind | None
    bottleneck: CommodityKind | None
    runs: bool


class FlowView(ApiModel):
    commodity: CommodityKind
    flow: str
    quantity: int


class QuoteView(ApiModel):
    commodity: CommodityKind
    price: int
    supply: int
    demand: int
    imported: int
    exported: int


class CommunityEconomyView(ApiModel):
    community_id: int
    epoch: int
    stocks: list[StockLotView]
    supply: dict[str, int]
    storage: dict[str, int]
    workshops: list[WorkshopView]
    chain: list[ChainStepView]
    flows: list[FlowView]
    quotes: list[QuoteView]
    currency_id: int | None
    market: bool


class WorkerView(ApiModel):
    community_id: int
    community_name: str
    workers: int


class RunView(ApiModel):
    epoch: int
    community_id: int
    quantity: int
    quality: int
    workers: int


class MechanicParamView(ApiModel):
    mechanic: str
    magnitude: int | None
    epochs: int | None


class ResourceProfileView(ApiModel):
    resource_id: int
    commodity: CommodityKind
    material: MaterialKind | None
    world_material_id: int | None
    material_label: str | None
    reserve: int
    initial_reserve: int
    richness: int
    regeneration: int
    extraction_difficulty: int
    required_branch: KnowledgeBranch | None
    required_level: int
    quality: int
    byproduct_material: MaterialKind | None
    byproduct_pct: int
    revealed: bool
    sealed_until_epoch: int | None
    last_output: int
    workers: list[WorkerView]
    runs: list[RunView]
    params: list[MechanicParamView]
    owners: list[int]


class PricePoint(ApiModel):
    epoch: int
    price: int
    supply: int
    demand: int
    imported: int
    exported: int


class PriceSeries(ApiModel):
    commodity: CommodityKind
    points: list[PricePoint]


class MarketView(ApiModel):
    market_id: int
    name: str
    world_id: int | None
    series: list[PriceSeries]


class TollView(ApiModel):
    region_id: int
    region_name: str
    controller_id: int
    controller_name: str
    rate_pct: int
    set_by_player: bool
    controller_held: bool
    polity_id: int | None
    polity_name: str


class RouteDangerView(ApiModel):
    bandits: int
    beasts: int
    weather: int
    sea: int


class RouteLossView(ApiModel):
    epoch: int
    commodity: CommodityKind
    cause: TradeLoss
    units: int
    culprit_id: int | None
    culprit_name: str


class RouteFlowView(ApiModel):
    epoch: int
    commodity: CommodityKind
    material: MaterialKind | None
    from_id: int
    to_id: int
    volume: int
    lost: int
    loss: TradeLoss | None
    value: int
    toll_paid: int


class TradeRouteView(ApiModel):
    route_id: int
    name: str
    world_id: int | None
    first_id: int
    first_name: str
    second_id: int
    second_name: str
    mode: TradeMode
    status: TradeRouteStatus
    length: int
    capacity: int
    danger: int
    renown: int
    culture: int
    path: list[int]
    tolls: list[TollView]
    controller_id: int | None
    blockaded_by_id: int | None
    founded_epoch: int
    last_traffic_epoch: int | None
    volume: int
    closed_by_player: bool
    closed_by_son_id: int | None
    closed_by_son_name: str
    dangers: RouteDangerView
    season_pct: int
    chokepoint: bool
    locked: list[str]
    untolled: list[int]
    region_names: dict[int, str]


class TradeRouteDetail(TradeRouteView):
    flows: list[RouteFlowView]
    losses: list[RouteLossView]


class CurrencyView(ApiModel):
    id: int
    name: str
    issuer_id: int
    issuer_name: str
    item_id: int | None
    metal: MaterialKind
    purity: int
    trust: int
    supply: int
    minted_epoch: int
    debased_epoch: int | None
    users: list[int]


class LoanView(ApiModel):
    id: int
    lender_id: int
    lender_name: str
    borrower_id: int
    borrower_name: str
    currency_id: int | None
    principal: int
    interest_pct: int
    repaid: int
    owed: int
    issued_epoch: int
    due_epoch: int
    status: LoanStatus
    purpose: str


class DebtView(ApiModel):
    bond_id: int
    debtor_id: int
    debtor_name: str
    creditor_id: int
    creditor_name: str
    amount: int
    what: str
    due_epoch: int | None
    currency_id: int | None


class LedgerView(ApiModel):
    loans: list[LoanView]
    debts: list[DebtView]


class MarketSummary(ApiModel):
    id: int
    name: str
    world_id: int | None
    entity_type: EntityType
