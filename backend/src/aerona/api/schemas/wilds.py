from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.ecology import BeastTemper, Diet, DomesticationStage, RangeTrend, SizeClass, Sociality, SpeciesUse
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
    rate: int


class HostView(ApiModel):
    disease: NodeRef | None
    immune: bool


class HerdView(ApiModel):
    community: NodeRef | None
    species: NodeRef | None
    head: int
    stage: DomesticationStage
    since_epoch: int
    fed_epochs: int
    locked: list[str]


class SpeciesCard(ApiModel):
    species_id: int
    body_plan: str
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
    locked: list[str]


class WebNode(ApiModel):
    species: NodeRef
    abundance: int
    diet: Diet
    size_class: SizeClass


class WebLink(ApiModel):
    hunter_id: int
    prey_id: int


class FoodWeb(ApiModel):
    region_id: int
    nodes: list[WebNode]
    links: list[WebLink]
