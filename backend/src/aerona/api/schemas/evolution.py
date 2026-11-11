from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import NodeRef
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.ecology import DomesticationStage
from aerona.domain.enums.evolution import EvolvedTrait, KeystoneRole, PlagueResponse, SuccessionStage, TrophicLevel


class StockTraitView(ApiModel):
    species: NodeRef | None
    region: NodeRef | None
    trait: EvolvedTrait
    mean: int
    variance: int
    updated_epoch: int
    locked: list[str]


class LineageMarkView(ApiModel):
    package: PackageKind
    blessing: bool
    source: NodeRef | None
    epoch: int
    locked: list[str]


class SpeciesEcologyView(ApiModel):
    keystone: KeystoneRole | None
    feral_epoch: int | None
    trophic_level: TrophicLevel | None
    stage: DomesticationStage
    locked: list[str]


class ServiceView(ApiModel):
    region: NodeRef | None
    role: KeystoneRole
    species: NodeRef | None
    strength: int
    epoch: int
    locked: list[str]


class TrophicView(ApiModel):
    level: TrophicLevel
    biomass: int
    cap: int
    epoch: int


class SuccessionView(ApiModel):
    succession: SuccessionStage
    succession_progress: int
    burned_epoch: int | None
    stage_cover: int
    locked: list[str]


class HerdRef(ApiModel):
    community: NodeRef | None
    species: NodeRef | None
    head: int
    stage: DomesticationStage


class PathogenView(ApiModel):
    cold_tolerance: int
    heat_tolerance: int
    resistance: int
    locked: list[str]


class CarrierView(ApiModel):
    mortal: NodeRef | None
    disease: NodeRef | None
    home_region: NodeRef | None
    identified: bool
    seeded: int
    since_epoch: int
    locked: list[str]


class PlagueResponseView(ApiModel):
    community: NodeRef | None
    disease: NodeRef | None
    response: PlagueResponse
    strength: int
    since_epoch: int
    until_epoch: int | None
    locked: list[str]


class CureResearchView(ApiModel):
    institution: NodeRef | None
    disease: NodeRef | None
    points: int
    threshold: int
    specimens: int
    started_epoch: int
    cured_epoch: int | None
    locked: list[str]


class WorldCycleView(ApiModel):
    carbon: int
    water: int
    nutrients: int
    carbon_in: int
    carbon_out: int
    water_in: int
    water_out: int
    nutrients_in: int
    nutrients_out: int
    updated_epoch: int
    locked: list[str]


class NodeEvolutionView(ApiModel):
    node: NodeRef
    species: SpeciesEcologyView | None
    traits: list[StockTraitView]
    marks: list[LineageMarkView]
    services: list[ServiceView]
    trophic: list[TrophicView]
    land: SuccessionView | None
    herds: list[HerdRef]
    pathogen: PathogenView | None
    carriers: list[CarrierView]
    responses: list[PlagueResponseView]
    research: list[CureResearchView]
    cycle: WorldCycleView | None
