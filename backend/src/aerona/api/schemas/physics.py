from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.cosmography import StarAge
from aerona.domain.enums.ecology import Biochemistry
from aerona.domain.enums.physics import CosmicFeatureKind, ImpactBody, ImpactOutcome, LifeComplexity, SurveyLevel, SystemRole, TerraformAim
from aerona.domain.enums.world import StarType


class StageSpan(ApiModel):
    stage: StarAge
    epochs: int


class SystemMember(ApiModel):
    star_id: int
    name: str
    star_type: StarType
    role: SystemRole
    mass: float
    luminosity: float


class SystemView(ApiModel):
    id: int
    name: str
    galaxy_id: int | None
    separation: float
    band_inner: float
    band_outer: float
    created_epoch: int
    locked: list[str]
    members: list[SystemMember]


class OrbitRecord(ApiModel):
    world_id: int
    name: str
    orbit: float
    eccentricity: float
    inclination: float
    parent_world_id: int | None
    habitable: bool
    ringed: bool
    tidally_locked: bool
    circumbinary: bool


class FeatureRecord(ApiModel):
    id: int
    kind: CosmicFeatureKind
    name: str
    galaxy_id: int | None
    star: NodeRef | None
    world: NodeRef | None
    world_b: NodeRef | None
    body: NodeRef | None
    route_id: int | None
    radius: float
    density: int
    radiation: int
    travel: int
    omen_weight: int
    richness: int
    pirates: int
    instability: int
    period_epochs: int
    next_return_epoch: int | None
    created_epoch: int
    ended_epoch: int | None
    locked: list[str]


class StarPhysicsView(ApiModel):
    star_id: int
    name: str
    star_type: StarType
    age_stage: StarAge
    mass: float
    metallicity: int
    age_epochs: int
    luminosity: float
    lifetime_epochs: int
    band_inner: float
    band_outer: float
    maker: NodeRef | None
    upkeep: int
    locked: list[str]
    stages: list[StageSpan]
    giant: StarType | None
    remnant: StarType
    supernova: bool
    engulf_orbit: float
    system: SystemView | None
    orbits: list[OrbitRecord]
    features: list[FeatureRecord]


class WorldPhysicsRecord(ApiModel):
    eccentricity: float
    inclination: float
    argument: float
    mass: float
    radius: float
    iron: int
    rock: int
    ice: int
    gas: int
    exotic: int
    rotation_hours: float
    nitrogen: int
    oxygen: int
    carbon_dioxide: int
    methane: int
    water_vapour: int
    exotic_gas: int
    pressure: float
    albedo: int
    tectonics: int
    volcanism: int
    hydrosphere: int
    cryosphere: int
    circumbinary: bool
    insolation: float
    surface_temperature: float
    gravity_g: float
    escape_velocity: float
    tidally_locked: bool
    ringed: bool
    aurora: int
    eclipse_years: int
    heat_shift: int
    sea_level: int
    habitable: bool
    locked: list[str]


class LifeRecord(ApiModel):
    complexity: LifeComplexity
    environments: list[str]
    biochemistries: list[Biochemistry]
    locked: list[str]


class TerraformRecord(ApiModel):
    id: int
    world: NodeRef | None
    aim: TerraformAim
    by: NodeRef | None
    step: int
    epochs_left: int
    started_epoch: int
    locked: list[str]


class ImpactRecord(ApiModel):
    id: int
    world: NodeRef | None
    region: NodeRef | None
    feature_id: int | None
    body: ImpactBody
    size: int
    due_epoch: int
    warned_epoch: int | None
    outcome: ImpactOutcome
    crater: NodeRef | None
    winter_epochs: int
    deflected_by: NodeRef | None
    called_by: NodeRef | None
    text: str
    locked: list[str]


class SurveyRecord(ApiModel):
    id: int
    observer: NodeRef | None
    world: NodeRef | None
    level: SurveyLevel
    epoch: int
    locked: list[str]


class FitRecord(ApiModel):
    people: NodeRef
    fit: int


class WorldPhysicsView(ApiModel):
    epoch: int
    world_id: int
    name: str
    year_length_days: int | None
    day_length_hours: int | None
    season_count: int | None
    axial_tilt: int | None
    tidal_strength: int | None
    physics: WorldPhysicsRecord | None
    life: LifeRecord | None
    terraforming: list[TerraformRecord]
    impacts: list[ImpactRecord]
    surveys: list[SurveyRecord]
    fits: list[FitRecord]


class HeavensPhysicsView(ApiModel):
    epoch: int
    systems: list[SystemView]
    features: list[FeatureRecord]
    impacts: list[ImpactRecord]
    terraforming: list[TerraformRecord]


class ObserverSurveyView(ApiModel):
    observer_id: int
    surveys: list[SurveyRecord]
