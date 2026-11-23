from aerona.api.schemas.common import ApiModel
from aerona.catalog.peoples import MountFit
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.death_work import RemainsTreatment
from aerona.domain.enums.demography import (
    AgeBand,
    CohortCondition,
    FuneralCustom,
    InheritanceCustom,
    Job,
    MartialStyle,
    MotifSource,
    NaturalTrait,
    SexKind,
)
from aerona.domain.enums.disease import ClimateMoisture, ClimateWarmth, CureSource, DiseaseTarget, OutbreakStatus, SpreadPath
from aerona.domain.enums.ecology import Biochemistry, Diet, SizeClass
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.mind import PressureKind, ValueAxis
from aerona.domain.enums.mortal import DeathCause, DeathReading
from aerona.domain.enums.physics import AirNeed
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind, SizeTier, TreasuryEntry, WaterSupply
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.world_view import SettleMode


class PopulationCohortView(ApiModel):
    age_band: AgeBand
    sex_kind: SexKind
    social_class: SocialClass
    condition: CohortCondition
    count: int


class LabourView(ApiModel):
    job: Job
    workers: int
    output_pct: int


class LabourFlowView(ApiModel):
    social_class: SocialClass
    job: Job
    workers: int


class SocietyPressureView(ApiModel):
    kind: PressureKind
    value: int


class LinkedRecord(ApiModel):
    id: int
    name: str


class WorkFactor(ApiModel):
    job: Job
    pct: int


class KinEffectsView(ApiModel):
    food_pct: int
    room_pct: int
    strength_pct: int
    disease_pct: int
    fleet_pct: int
    mount: MountFit
    hunger_pct: int
    work: list[WorkFactor]


class BiologyView(ApiModel):
    maturity_years: int
    adult_years: int
    elder_years: int
    fertility_pct: int
    acclimatised: TemperatureBand
    staple: CommodityKind
    traits: list[NaturalTrait]
    immunities: list[LinkedRecord]
    body_plan: BodyPlan
    size_class: SizeClass
    diet: Diet
    edible: list[CommodityKind]
    effects: KinEffectsView
    biochemistry: Biochemistry = Biochemistry.CARBON_WATER
    air: AirNeed = AirNeed.OXYGEN
    gravity_low: int = 50
    gravity_high: int = 160
    habitability: int = 100
    locked: list[str]


class MartialRecordView(ApiModel):
    style: MartialStyle
    wins: int
    losses: int


class DeathReadingView(ApiModel):
    cause: DeathCause
    reading: DeathReading
    authored: bool
    held: bool


class CultureView(ApiModel):
    cohesion: int
    literacy: int
    urbanisation: int
    ornament: int
    geometry: int
    colour: int
    scale: int
    symmetry: int
    motif_sources: list[MotifSource]
    martial_style: MartialStyle
    inheritance: InheritanceCustom
    slavery_lawful: bool
    staples: list[CommodityKind]
    liturgical_language: LinkedRecord | None
    trade_language: LinkedRecord | None
    funeral_rite: FuneralCustom
    remains_treatment: RemainsTreatment
    funeral_tradition: LinkedRecord | None
    death_readings: list[DeathReadingView]
    martial_record: list[MartialRecordView]
    martial_net: int
    locked: list[str]


class ValuePoint(ApiModel):
    axis: ValueAxis
    value: int


class NeighbourCulture(ApiModel):
    entity_id: int
    name: str
    values: list[ValuePoint]


class ClassMood(ApiModel):
    social_class: SocialClass
    share: float
    satisfaction: int


class DemographyView(ApiModel):
    entity_id: int
    people_id: int | None
    sex_kinds: list[SexKind]
    cohorts: list[PopulationCohortView]
    labour: list[LabourView]
    flows: list[LabourFlowView]
    pressures: list[SocietyPressureView]
    classes: list[ClassMood]
    biology: BiologyView | None
    culture: CultureView | None
    values: list[ValuePoint]
    neighbours: list[NeighbourCulture]
    inequality: int
    mobilisation_pct: int
    afflictions: list["AfflictionView"]
    named: list["NamedMortalView"]
    held: list[str]


class AfflictionView(ApiModel):
    disease_id: int
    disease: str
    primary_route: Transmission
    target_functions: list[DiseaseTarget]
    severity: int
    status: OutbreakStatus
    outbreak_id: int


class NamedMortalView(ApiModel):
    id: int
    name: str
    dormant: bool
    held: bool
    importance: int


class ImmunityView(ApiModel):
    community_id: int
    community: str
    age_band: AgeBand
    immune_pct: int
    locked: bool


class OutbreakView(ApiModel):
    season_factor: int = 100
    id: int
    disease_id: int
    disease: str
    region_id: int
    region: str
    source_region_id: int | None
    path: SpreadPath
    status: OutbreakStatus
    severity: int
    infected: int
    dead: int
    started_epoch: int
    ended_epoch: int | None
    quarantined: bool
    event_id: int | None
    locked: list[str]
    unseen_pct: int


class StrainView(ApiModel):
    id: int
    name: str
    generation: int
    virulence: int
    lethality: int


class EndemicView(ApiModel):
    region_id: int
    region: str
    load: int
    since_epoch: int
    locked: bool
    disease_id: int
    disease: str


class CureView(ApiModel):
    community_id: int
    community: str
    source: CureSource
    since_epoch: int


class DiseaseRouteView(ApiModel):
    route: Transmission
    share: int
    held: bool


class DiseaseView(ApiModel):
    entity_id: int
    name: str
    primary_route: Transmission
    primary_share: int
    routes: list[DiseaseRouteView]
    virulence: int
    lethality: int
    chronic_rate: int
    incubation: int
    target_functions: list[DiseaseTarget]
    affinity_warmth: ClimateWarmth
    affinity_moisture: ClimateMoisture
    host_species_id: int | None
    immunity_epochs: int
    mutation_rate: int
    stigma: int
    cure_level: int
    generation: int
    parent_id: int | None
    origin_region_id: int | None
    emerged_epoch: int
    locked: list[str]
    origin_incident_id: int | None
    origin: "IncidentRefView | None"
    incidents: list["IncidentRefView"]
    hosts: list["FeastHostView"]
    unseen_pct: int
    sick: int
    strains: list[StrainView]
    outbreaks: list[OutbreakView]
    endemic: list[EndemicView]
    cures: list[CureView]
    immunities: list[ImmunityView]


class IncidentRefView(ApiModel):
    id: int
    epoch: int
    year: int | None
    kind: str
    text: str
    place_id: int | None


class FeastHostView(ApiModel):
    species_id: int
    name: str
    immune: bool
    lands: int
    abundance: int
    primary: bool


class DistrictView(ApiModel):
    id: int
    kind: DistrictKind
    level: int
    condition: int
    material: BuildMaterial
    world_material_id: int | None
    built_epoch: int
    design_id: int | None
    locked: list[str]
    effects: dict[str, int]


class DistrictDesignView(ApiModel):
    id: int
    name: str
    description: str | None
    base_kind: DistrictKind
    parameters: dict[str, int | None]
    defaults: dict[str, int]
    created_epoch: int


class ArmyOption(ApiModel):
    id: int
    name: str
    size: int


class AdminView(ApiModel):
    base: int
    literacy: int
    scribes: int
    writing: int
    palace: int
    total: int


class StorageView(ApiModel):
    districts: int
    workshops: int
    other: int
    total: int


class DefenceView(ApiModel):
    wall_pct: int
    tower_pct: int
    batter_pct: int
    gate_weakness_pct: int


class DistrictEffectsView(ApiModel):
    housing: int
    food_store: int
    goods_store: int
    harbour: int
    order: int
    sanitation: int
    piety_floor: int
    admin_pct: int
    policing: int
    investment_pct: int
    tension_relief_pct: int


class InfrastructureView(ApiModel):
    walls_level: int
    walls_material: BuildMaterial
    walls_world_material_id: int | None
    walls_condition: int
    gates: int
    roads: int
    water: WaterSupply
    sewers: bool
    granary_capacity: int
    warehouse_capacity: int
    harbour_capacity: int
    towers: int
    bridges: int = 0
    irrigation: int = 0
    locked: list[str]


class TreasuryLine(ApiModel):
    epoch: int
    entry: TreasuryEntry
    amount: int
    balance: int
    note: str | None


class HistoryPoint(ApiModel):
    epoch: int
    size_tier: SizeTier
    public_order: int
    crime: int
    unrest: int
    sanitation: int
    wealth: int
    treasury: int
    population: int


class ForeignShare(ApiModel):
    people_id: int
    name: str
    share: int


class SettlementPlanView(ApiModel):
    entity_id: int
    world_id: int | None
    size_tier: SizeTier
    settle_mode: SettleMode
    treasury: int
    tax_rate: int
    public_order: int
    crime: int
    unrest: int
    sanitation: int
    fire_risk: int
    wealth: int
    prestige: int
    militia: int
    garrison_id: int | None
    free_city: bool
    charter_id: int | None
    siege_supplies: int
    siege_water: int
    siege_disease: int
    investment_pool: int
    construction_capacity: int
    hauling_capacity: int
    rationing: bool
    admin_capacity: int
    admin: AdminView
    food_storage: StorageView
    goods_storage: StorageView
    defences: DefenceView
    district_effects: DistrictEffectsView
    prestige_pull_pct: int
    prestige_investment_pct: int
    designs: list[DistrictDesignView]
    kind_defaults: dict[DistrictKind, dict[str, int]]
    armies: list[ArmyOption]
    district_slots: int
    housing: int
    locked: list[str]
    foreigners: list[ForeignShare]
    infrastructure: InfrastructureView
    districts: list[DistrictView]
    treasury_ledger: list[TreasuryLine]
    history: list[HistoryPoint]


DemographyView.model_rebuild()
DiseaseView.model_rebuild()
