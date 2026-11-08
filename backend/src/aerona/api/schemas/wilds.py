from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.ecology import (
    BeastTemper,
    Biochemistry,
    Cultivation,
    Diet,
    DomesticationStage,
    FoodLink,
    GrowthCycle,
    PlantYield,
    RangeTrend,
    SizeClass,
    Sociality,
    SpeciesClass,
    SpeciesUse,
)
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import CreatureTrait


class RangeView(ApiModel):
    region: NodeRef | None
    abundance: int
    trend: RangeTrend
    fit: int
    hunted: int
    since_epoch: int
    locked: list[str]


class YieldView(ApiModel):
    product: str
    commodity: CommodityKind | None
    material: MaterialKind | None
    world_material_id: int | None
    world_material: str | None
    rate: int


class HostView(ApiModel):
    disease: NodeRef | None
    immune: bool
    locked: list[str]


class CustomUseView(ApiModel):
    kind_id: int
    name: str
    base_use: SpeciesUse
    output_pct: int


class UseKindView(ApiModel):
    id: int
    name: str
    base_use: SpeciesUse
    output_pct: int
    description: str | None
    locked: list[str]
    species: list[NodeRef]


class TotemView(ApiModel):
    people_id: int
    species: NodeRef | None
    tradition: NodeRef | None


class RangeCell(ApiModel):
    region: NodeRef
    abundance: int
    trend: RangeTrend
    fit: int


class SpeciesRangeMap(ApiModel):
    species_id: int
    world_id: int | None
    peak: int
    cells: list[RangeCell]


class BeastTributeView(ApiModel):
    town: NodeRef | None
    treaty: NodeRef | None
    commodity: CommodityKind
    units: int
    last_kept_epoch: int | None


class HerdView(ApiModel):
    community: NodeRef | None
    species: NodeRef | None
    head: int
    stage: DomesticationStage
    since_epoch: int
    fed_epochs: int
    locked: list[str]


class PlantView(ApiModel):
    growth_cycle: GrowthCycle
    growing_seasons: int
    soil_need: int
    cultivation: Cultivation
    cultivar_of: NodeRef | None
    since_epoch: int
    locked: list[str]


class SownView(ApiModel):
    region: NodeRef | None
    share: int
    fit: int
    since_epoch: int
    locked: list[str]


class SpeciesCard(ApiModel):
    species_id: int
    world_id: int | None
    species_class: SpeciesClass
    biochemistry: Biochemistry
    bearable: bool
    plant: PlantView | None
    sown_in: list[SownView]
    pests: list[NodeRef]
    pest_of: list[NodeRef]
    body_plan: BodyPlan
    size_class: SizeClass
    lifespan_years: int
    maturity_years: int
    litter_size: int
    breeding_seasons: int
    diet: Diet
    metabolism: int
    habitat: dict[str, int]
    temperature_min: int
    temperature_max: int
    water_need: int
    altitude_min: int
    altitude_max: int
    nocturnal: bool
    migratory: bool
    migration_path: list[NodeRef]
    aggression: int
    territoriality: int
    sociality: Sociality
    cunning: int
    fear_of_people: int
    tameability: int
    stage: DomesticationStage
    domesticated_from: NodeRef | None
    sacred_to: NodeRef | None
    traits: list[CreatureTrait]
    uses: list[SpeciesUse]
    yields: list[YieldView]
    hosts: list[HostView]
    ranges: list[RangeView]
    herds: list[HerdView]
    hunts: list[NodeRef]
    hunted_by: list[NodeRef]
    descendants: list[NodeRef]
    beasts: list[NodeRef]
    pinned_prey: list[NodeRef]
    barred_prey: list[NodeRef]
    custom_uses: list[CustomUseView]
    totem_of: list[NodeRef]
    abundance: int
    stage_epoch: int
    locked: list[str]


class WoundView(ApiModel):
    by: NodeRef | None
    epoch: int


class BeastWound(ApiModel):
    part: str
    kind: str
    severity: int
    state: str
    function_loss: int


class BeastCard(ApiModel):
    beast_id: int
    species: NodeRef | None
    endurance: int
    perception: int
    willpower: int
    intelligence: int
    age: int
    lifespan: int
    size_class: SizeClass
    lair: NodeRef | None
    temper: BeastTemper
    bound_to: NodeRef | None
    hoard: dict[str, int]
    raids: int
    woke_epoch: int | None
    terror: int
    renown: int
    wounds: list[WoundView]
    injuries: list[BeastWound]
    body_plan: str | None
    hp: int
    treasures: list[NodeRef]
    tributes: list[BeastTributeView]
    reach: int
    harm_taken_pct: int
    wake_pct: int
    tame_pct: int
    rest_pct: int
    rideable: bool
    locked: list[str]


class WebNode(ApiModel):
    species: NodeRef
    abundance: int
    diet: Diet
    size_class: SizeClass


class WebLink(ApiModel):
    hunter_id: int
    prey_id: int
    kind: FoodLink


class FoodWeb(ApiModel):
    region_id: int
    nodes: list[WebNode]
    links: list[WebLink]


class CropView(ApiModel):
    plant: NodeRef | None
    share: int
    fit: int
    cultivation: Cultivation | None
    products: list[PlantYield]
    pests: list[NodeRef]
    since_epoch: int
    locked: list[str]


class RegionCrops(ApiModel):
    region_id: int
    world_id: int | None
    harvest_pct: int
    crop_cap: int
    crops: list[CropView]


class LifeKind(ApiModel):
    biochemistry: Biochemistry
    label: str
    borne: bool
    anywhere: bool
    kinds: int


class WorldLife(ApiModel):
    world_id: int
    kinds: list[LifeKind]
