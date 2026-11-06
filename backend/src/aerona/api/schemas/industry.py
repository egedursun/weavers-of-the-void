from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.mind import LabelView
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.industry import EnergyKind, MethodKind, ProcessKind, QualityTier
from aerona.domain.enums.material import MaterialKind


class WorksOptionView(ApiModel):
    method: MethodKind
    label: str
    summary: str
    energy: EnergyKind
    energy_need: int
    output_pct: int
    quality_bonus: int
    air: int
    water: int
    soil: int
    tool_wear: int
    blocked: str | None


class WorksMethodView(ApiModel):
    process: ProcessKind
    process_label: str
    method: MethodKind
    label: str
    summary: str
    chosen: bool
    adopted_epoch: int | None
    displaced: int
    held: bool
    options: list[WorksOptionView]


class WorksEnergyView(ApiModel):
    kind: EnergyKind
    label: str
    source: str
    supply: int
    spent: int
    short: int
    held: bool


class WorksStockView(ApiModel):
    id: int
    commodity: CommodityKind
    label: str
    material: MaterialKind | None
    world_material_id: int | None
    quantity: int
    quality: int
    tier: QualityTier
    tier_label: str
    preserved: int
    perishable: bool
    held: bool


class WorksPolluterView(ApiModel):
    community: NodeRef | None
    units: int


class WorksPollutionView(ApiModel):
    region: NodeRef | None
    air: int
    water: int
    soil: int
    blight: int
    epoch: int | None
    held: list[str]
    polluters: list[WorksPolluterView]


class WorksStoresView(ApiModel):
    heat_need: int
    tools_worn: int
    spoiled: int
    preserved: int
    meal_quality: int
    meal_tier: QualityTier
    meal_tier_label: str
    epoch: int | None
    held: list[str]


class WorksView(ApiModel):
    node_id: int
    name: str
    community: bool
    methods: list[WorksMethodView]
    energy: list[WorksEnergyView]
    stores: WorksStoresView | None
    stocks: list[WorksStockView]
    pollution: list[WorksPollutionView]
    tiers: list[LabelView]
    processes: list[LabelView]
