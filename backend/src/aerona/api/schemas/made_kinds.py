from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.body import DamageType
from aerona.domain.enums.collective import DesignComponentKind, DesignKind
from aerona.domain.enums.cuisine import CookingMethod, DishCourse
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.demography import MartialStyle
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.equipment import ArmamentSlot, EquipmentFamily
from aerona.domain.enums.integrity import Criticality, SectionHazard, SectionState
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.military import ArmourType, Formation, ShieldType, UnitFamily, UnitKind
from aerona.domain.enums.mortal import MortalSex
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.structure import BuildingForm, BuildScale, SectionRole, StaffScale, StructureKind, StructureSection
from aerona.domain.enums.vehicles import (
    FireControl,
    MountArc,
    MountKind,
    Propulsion,
    VehicleDomain,
    VehicleFamily,
    VehicleFrame,
    VehicleSection,
    VehicleSize,
    VehicleStatus,
)


class VehicleSectionView(ApiModel):
    section: VehicleSection
    function: DesignComponentKind
    criticality: Criticality
    share: int
    exposure: int
    armour: int
    hazard: SectionHazard
    neighbours: list[VehicleSection]
    material_id: int | None
    material_name: str | None
    size: int
    quality: int
    locked: list[str]


class MountView(ApiModel):
    id: int
    slot: int
    mount: MountKind
    section: VehicleSection | None
    model_id: int | None
    model_name: str | None
    count: int
    arc: MountArc
    locked: list[str]


class VehicleTypeView(ApiModel):
    id: int
    name: str
    description: str | None
    world_id: int | None
    origin: NodeRef | None
    owner: NodeRef | None
    designer: NodeRef | None
    kind: DesignKind
    frame: VehicleFrame | None
    frame_label: str | None
    domain: VehicleDomain | None
    family: VehicleFamily | None
    propulsion: Propulsion | None
    size_class: VehicleSize
    mass: int
    speed: int
    range: int
    seaworthiness: int
    cargo: int
    armament: int
    crew: int
    troops: int
    armour: int
    structure: int
    fuel: CommodityKind | None
    fuel_use: int
    cost: int
    upkeep: int
    tech_level: int
    strangeness: int
    fire_control: FireControl
    parent_design_id: int | None
    obsolete: bool
    epoch: int
    built: int
    sections: list[VehicleSectionView]
    mounts: list[MountView]
    techniques: list[Technique]
    locked: list[str]


class LoadoutView(ApiModel):
    model_id: int
    model_name: str
    family: EquipmentFamily
    slot: ArmamentSlot
    count: int


class UnitTypeView(ApiModel):
    id: int
    name: str
    description: str | None
    world_id: int | None
    origin: NodeRef | None
    owner: NodeRef | None
    base_kind: UnitKind
    role_label: str
    family: UnitFamily
    melee: int
    missile: int
    defence: int
    speed: int
    mass: int
    cost: int
    upkeep: int
    armour: ArmourType
    shield: ShieldType
    terror: int
    counters_charge: bool
    flying: bool
    social_class: SocialClass | None
    reach: int
    volleys: int
    accuracy: int
    piercing: int
    doctrine: MartialStyle | None
    formation: Formation | None
    discipline: int
    training_epochs: int
    mount_species: NodeRef | None
    vehicle_design_id: int | None
    vehicle_design_name: str | None
    crew_per_vehicle: int
    parent_design_id: int | None
    retired: bool
    created_epoch: int
    fielded: int
    loadout: list[LoadoutView]
    techniques: list[Technique]
    locked: list[str]


class EquipmentModelView(ApiModel):
    id: int
    name: str
    description: str | None
    world_id: int | None
    origin: NodeRef | None
    slot: ArmamentSlot
    family: EquipmentFamily
    family_label: str
    material: MaterialKind | None
    world_material_id: int | None
    material_name: str | None
    quality: int
    technique: Technique | None
    tech_level: int
    damage: int
    piercing: int
    reach: int
    rate: int
    accuracy: int
    damage_type: DamageType
    ammunition: CommodityKind | None
    crew: int
    protection: int
    coverage: int
    weight: int
    cost: int
    renown: int
    parent_model_id: int | None
    created_epoch: int
    retired: bool
    stored: int
    carried: int
    locked: list[str]


class IngredientView(ApiModel):
    commodity: CommodityKind
    share: int


class CookingView(ApiModel):
    community: NodeRef
    dish_id: int
    dish_name: str
    popularity: int
    cooked: int
    since_epoch: int
    locked: list[str]


class DishView(ApiModel):
    id: int
    name: str
    description: str | None
    world_id: int | None
    origin: NodeRef | None
    method: CookingMethod
    course: DishCourse
    nourishment: int
    delight: int
    keeps: int
    prestige: int
    technique: Technique | None
    created_epoch: int
    retired: bool
    ingredients: list[IngredientView]
    cooked_in: list[CookingView]
    locked: list[str]


class StructureSectionView(ApiModel):
    section: StructureSection
    role: SectionRole
    criticality: Criticality
    share: int
    exposure: int
    hazard: SectionHazard
    neighbours: list[StructureSection]
    condition: int
    state: SectionState
    material: MaterialKind | None
    world_material_id: int | None
    flammability: int
    laid: bool
    locked: list[str]


class DesignSectionView(ApiModel):
    section: StructureSection
    criticality: Criticality
    share: int
    material: MaterialKind | None


class MegastructureView(ApiModel):
    kind: StructureKind
    target_orbit: float | None
    output: int
    updated_epoch: int
    locked: list[str]


class BuildingTypeView(ApiModel):
    id: int
    name: str
    description: str | None
    world_id: int | None
    origin: NodeRef | None
    base_kind: StructureKind
    kind_label: str
    form: BuildingForm | None
    storeys: int | None
    material: MaterialKind | None
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
    created_epoch: int
    used_by: int
    sections: list[DesignSectionView]
    locked: list[str]


class WorldKindsView(ApiModel):
    world_id: int
    vehicle_types: list[VehicleTypeView]
    unit_types: list[UnitTypeView]
    equipment_models: list[EquipmentModelView]
    dishes: list[DishView]
    building_types: list[BuildingTypeView]


class GroupSectionView(ApiModel):
    section: VehicleSection
    criticality: Criticality
    damaged: int
    disabled: int
    destroyed: int
    locked: list[str]


class VehicleGroupView(ApiModel):
    id: int
    holder: NodeRef
    design_id: int
    design_name: str
    frame: VehicleFrame | None
    family: VehicleFamily | None
    domain: VehicleDomain | None
    count: int
    crewed: int
    condition: int
    fuel: int
    status: VehicleStatus
    region: NodeRef | None
    built_epoch: int
    firepower: int
    armour: int
    pace: int
    troops: int
    cargo: int
    crew_needed: int
    sections: list[GroupSectionView]
    locked: list[str]


class StoreView(ApiModel):
    model_id: int
    model_name: str
    family: EquipmentFamily
    slot: ArmamentSlot
    count: int
    locked: list[str]


class CarriedView(ApiModel):
    model_id: int
    model_name: str
    family: EquipmentFamily
    slot: ArmamentSlot
    count: int
    condition: int
    locked: list[str]


class StackKitView(ApiModel):
    unit_id: int
    kind: UnitKind
    count: int
    design_id: int | None
    design_name: str | None
    carried: list[CarriedView]


class VesselSectionView(ApiModel):
    section: VehicleSection
    criticality: Criticality
    state: SectionState
    condition: int
    laid: bool
    locked: list[str]


class AttractionView(ApiModel):
    drawn_to: list[MortalSex] | None
    attraction: int
    decline: int
    held: list[str]


class KindRef(ApiModel):
    id: int
    name: str
    family: str


class OwnKindsView(ApiModel):
    vehicle_types: list[KindRef]
    unit_types: list[KindRef]
    equipment_models: list[KindRef]
    dishes: list[KindRef]
    building_types: list[KindRef]


class ThingKindsView(ApiModel):
    node: NodeRef
    world_id: int | None
    vehicle_groups: list[VehicleGroupView]
    stores: list[StoreView]
    stacks: list[StackKitView]
    pace: int | None
    vessel_sections: list[VesselSectionView]
    cooking: list[CookingView]
    sections: list[StructureSectionView]
    megastructure: MegastructureView | None
    attraction: AttractionView | None
    own: OwnKindsView
