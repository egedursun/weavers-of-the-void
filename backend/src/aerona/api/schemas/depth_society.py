from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.demography import Aesthetic, AgeBand, CohortCondition, InheritanceCustom, Job, MarriageCustom, MartialStyle, Sex
from aerona.domain.enums.disease import ClimateAffinity, CureSource, DiseaseTarget, DiseaseVector, OutbreakStatus, SpreadPath
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.mind import PressureKind, ValueAxis
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind, SizeTier, TreasuryEntry, WaterSupply
from aerona.domain.enums.society import SocialClass


class PopulationCohortView(ApiModel):
    age_band: AgeBand
    sex: Sex
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


class PressureView(ApiModel):
    kind: PressureKind
    value: int


class BiologyView(ApiModel):
    maturity_years: int
    adult_years: int
    elder_years: int
    fertility_pct: int
    acclimatised: TemperatureBand
    staple: CommodityKind
    traits: list[str]
    locked: list[str]


class CultureView(ApiModel):
    cohesion: int
    literacy: int
    urbanisation: int
    aesthetic: Aesthetic
    martial_style: MartialStyle
    marriage: MarriageCustom
    endogamous: bool
    inheritance: InheritanceCustom
    slavery_lawful: bool
    staples: list[str]
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
    cohorts: list[PopulationCohortView]
    labour: list[LabourView]
    flows: list[LabourFlowView]
    pressures: list[PressureView]
    classes: list[ClassMood]
    biology: BiologyView | None
    culture: CultureView | None
    values: list[ValuePoint]
    neighbours: list[NeighbourCulture]
    inequality: int
    mobilisation_pct: int


class ImmunityView(ApiModel):
    community_id: int
    community: str
    age_band: AgeBand
    immune_pct: int


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


class CureView(ApiModel):
    community_id: int
    community: str
    source: CureSource
    since_epoch: int


class DiseaseView(ApiModel):
    entity_id: int
    name: str
    vector: DiseaseVector
    virulence: int
    lethality: int
    chronic_rate: int
    incubation: int
    target_functions: list[DiseaseTarget]
    climate_affinity: ClimateAffinity
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
    strains: list[StrainView]
    outbreaks: list[OutbreakView]
    endemic: list[EndemicView]
    cures: list[CureView]
    immunities: list[ImmunityView]


class QuarantineView(ApiModel):
    region_id: int
    region: str
    until_epoch: int


class OutbreakMapView(ApiModel):
    world_id: int
    outbreaks: list[OutbreakView]
    endemic: list[EndemicView]
    quarantines: list[QuarantineView]


class DistrictView(ApiModel):
    id: int
    kind: DistrictKind
    level: int
    condition: int
    material: BuildMaterial
    built_epoch: int


class InfrastructureView(ApiModel):
    walls_level: int
    walls_material: BuildMaterial
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
    size_tier: SizeTier
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
    district_slots: int
    housing: int
    locked: list[str]
    foreigners: list[ForeignShare]
    infrastructure: InfrastructureView
    districts: list[DistrictView]
    treasury_ledger: list[TreasuryLine]
    history: list[HistoryPoint]
