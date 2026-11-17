from pydantic import Field

from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.economy import (
    CommodityFamily,
    CommodityKind,
    CurrencyIssuer,
    ExtractionKind,
    FoeNature,
    GoodsFlow,
    LoanStatus,
    MaterialFamily,
    MaterialOrigin,
    MaterialSlot,
    MoneyBacking,
    MoneyForm,
    TradeLoss,
    TradeMode,
    TradeRouteStatus,
    WorkshopKind,
)
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.nature_kinds import MaterialSource
from aerona.domain.enums.polity import DebtRemedy
from aerona.domain.enums.society import KnowledgeBranch, ResourceMechanic


class MaterialView(ApiModel):
    kind: MaterialKind | None
    world_material_id: int | None
    label: str
    family: MaterialFamily
    origin: MaterialOrigin
    source: MaterialSource
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
    melting_point: int
    ignition_point: int
    boiling_point: int
    density: int
    impact_yield: int
    impact_fracture: int
    shear_yield: int
    shear_fracture: int
    elasticity: int
    thermal_conductivity: int
    solid_density: int
    max_edge: int
    branch: KnowledgeBranch | None
    level: int
    gate: KnowledgeBranch | None
    description: str | None = None
    deposit_id: int | None = None
    held: bool = False
    base_kind: MaterialKind | None = None
    price_premium_pct: int = 100
    worth_pct: int = 100


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
    held: bool = False


class WorkshopView(ApiModel):
    kind: WorkshopKind
    label: str
    level: int
    fleet: int
    idle_epochs: int
    built_epoch: int
    structure_id: int | None
    held: bool = False
    design_id: int | None = None


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
    flow: GoodsFlow
    quantity: int


class QuoteView(ApiModel):
    commodity: CommodityKind
    price: int
    supply: int
    demand: int
    imported: int
    exported: int
    swing: int = 0


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
    held: bool = False


class RunView(ApiModel):
    epoch: int
    community_id: int
    quantity: int
    quality: int
    workers: int


class MechanicParamView(ApiModel):
    mechanic: ResourceMechanic
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
    extraction: ExtractionKind
    required_branch: KnowledgeBranch | None
    required_level: int
    quality: int
    byproduct_material: MaterialKind | None
    byproduct_pct: int
    revealed: bool
    sealed_until_epoch: int | None
    last_output: int
    held: bool = False
    knowledge_gated: list[int] = Field(default_factory=list)
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
    swing: int = 0


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
    metal: MaterialKind | None
    purity: int
    trust: int
    supply: int
    minted_epoch: int
    debased_epoch: int | None
    form: MoneyForm
    backing: MoneyBacking
    convertible: bool
    issuer_kind: CurrencyIssuer
    users: list[int]
    held: bool = False


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
    held: bool = False
    borrower_type: EntityType | None = None
    currency_name: str | None = None


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
    currency_name: str | None = None
    remedy: DebtRemedy | None = None


class LedgerView(ApiModel):
    loans: list[LoanView]
    debts: list[DebtView]


class MarketSummary(ApiModel):
    id: int
    name: str
    world_id: int | None
    entity_type: EntityType


class MaterialSlotView(ApiModel):
    slot: MaterialSlot
    material: MaterialKind | None
    world_material_id: int | None
    label: str
    family: MaterialFamily
    held: bool
    hardness: int
    toughness: int
    weight: int
    sanctity: int
    corruption: int
    rarity: int
    base_value: int
    decay: int
    melting_point: int
    ignition_point: int
    boiling_point: int
    density: int
    impact_yield: int
    impact_fracture: int
    shear_yield: int
    shear_fracture: int
    elasticity: int
    thermal_conductivity: int
    solid_density: int
    max_edge: int
    effects: dict[str, int]


class NodeMaterialsView(ApiModel):
    node_id: int
    entity_type: EntityType
    world_id: int | None
    slots: list[MaterialSlotView]
    open_slots: list[MaterialSlot]
    foe_natures: list[FoeNature]


class PremiumView(ApiModel):
    commodity: CommodityKind
    premium_pct: int
    held_price: int | None
    held_supply: int | None


class MarketHoldsView(ApiModel):
    market_id: int
    premiums: list[PremiumView]


class DebtLawView(ApiModel):
    law_id: int
    name: str
    holders: list[int]
    holder_names: list[str]
    remedy: DebtRemedy
    jubilee_epochs: int
    enforcement: int


class WorkshopDesignView(ApiModel):
    id: int
    world_id: int
    base_kind: WorkshopKind
    label: str
    name: str
    description: str | None
    output_pct: int
    capacity_pct: int
    store_pct: int
    quality_bonus: int
    held: bool
    workshops: int
