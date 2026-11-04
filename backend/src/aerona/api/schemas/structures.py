from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.demography import Aesthetic
from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.structure import (
    BuilderKind,
    BuildScale,
    CapacityUnit,
    ConstructionState,
    ConstructionStatus,
    StaffScale,
    StructureGroup,
    StructureKind,
)


class FunctionBreakdownView(ApiModel):
    base: int
    design_pct: int
    condition_pct: int
    staff_pct: int
    ley_pct: int
    effect_pct: int
    threshold: int


class ConstructionView(ApiModel):
    id: int
    status: ConstructionStatus
    cost: int
    work: int
    percent: int
    funds: int
    workers: int
    materials_pct: int
    stalled_epochs: int
    stall_limit: int
    generations: int
    started_epoch: int
    finished_epoch: int | None
    player: bool
    locked: list[str]


class StructureView(ApiModel):
    id: int
    name: str
    status: EntityStatus
    kind: StructureKind
    group: StructureGroup
    label: str
    design_id: int | None
    design_name: str | None
    level: int
    capacity: int
    capacity_unit: CapacityUnit
    condition: int
    durability: int
    construction_state: ConstructionState
    progress: int
    fire_resistance: int
    material: MaterialKind | None
    world_material_id: int | None
    material_label: str | None
    host_id: int | None
    host_name: str | None
    builder_id: int | None
    builder_name: str | None
    builder_kind: BuilderKind | None
    architect_id: int | None
    architect_name: str | None
    dedicated_son_id: int | None
    dedicated_son_name: str | None
    aesthetic: Aesthetic | None
    on_ley_line: bool
    attuned: bool
    anchor: bool
    splendor: int
    function: int
    effect_pct: int
    staff_pct: int
    staff_class: SocialClass | None
    staff_required: int
    staff_allocated: int
    staff_held: bool
    upkeep_coin: int
    upkeep_goods: int
    upkeep_commodity: CommodityKind
    unpaid_epochs: int
    built_epoch: int | None
    workshop: WorkshopKind | None
    min_tier: SizeTier
    scale: BuildScale
    locked: list[str]
    breakdown: FunctionBreakdownView
    construction: ConstructionView | None


class KindOptionView(ApiModel):
    kind: StructureKind
    group: StructureGroup
    label: str
    min_tier: SizeTier
    allowed: bool
    scale: BuildScale
    cost: int
    capacity_unit: CapacityUnit
    staff_class: SocialClass | None
    staff_scale: StaffScale
    present: int


class DesignView(ApiModel):
    id: int
    world_id: int | None
    name: str
    description: str | None
    base_kind: StructureKind
    staff_class: SocialClass | None
    staff_scale: StaffScale | None
    scale: BuildScale | None
    upkeep_commodity: CommodityKind | None
    min_tier: SizeTier | None
    ley: bool | None
    capacity_pct: int
    cost_pct: int
    upkeep_pct: int
    function_pct: int
    staff_pct: int
    retired: bool
    used_by: int
    locked: list[str]


class SettlementStructuresView(ApiModel):
    host_id: int
    world_id: int | None
    size_tier: SizeTier | None
    slots_total: int
    slots_used: int
    structures: list[StructureView]
    kinds: list[KindOptionView]
    designs: list[DesignView]
