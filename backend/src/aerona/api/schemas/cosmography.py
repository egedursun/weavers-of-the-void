from pydantic import Field

from aerona.api.schemas.common import ApiModel
from aerona.api.schemas.records import ChronicleLineRecord, ImageRecord, NodeRef, StarRecord
from aerona.domain.enums.cosmography import (
    ApocalypseVariant,
    BeingAgenda,
    BeingKind,
    BeingPhase,
    BeingScale,
    Causality,
    ClusterKind,
    DimensionalEventKind,
    DimensionElement,
    DimensionKind,
    GalacticEventKind,
    GalacticNucleus,
    GalacticStructureKind,
    GalacticZone,
    GalaxyAge,
    GalaxyType,
    OmenReading,
    PhenomenonCause,
    PhenomenonKind,
    RiftCause,
    RiftState,
    RouteScope,
    SkyObject,
)
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faith import StratumKind
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.enums.world import Discovery
from aerona.domain.models.profiles import EntityDepth


class DimensionRecord(ApiModel):
    id: int
    name: str
    dimension_kind: DimensionKind
    element: DimensionElement | None
    parent_dimension_id: int | None
    veil: int
    stability: int
    time_factor: float
    magic: int
    hostility: int
    sanity_drain: int
    leak: int
    causality: Causality
    discovery: Discovery
    ruler_node_id: int | None
    description: str | None
    image_prompt: str | None
    created_epoch: int
    locked: list[str]


class ClusterRecord(ApiModel):
    id: int
    name: str
    cluster_kind: ClusterKind
    parent_cluster_id: int | None
    dimension_id: int | None
    x: float
    y: float
    radius: float
    medium_heat: int
    expansion: int
    discovery: Discovery
    description: str | None
    image_prompt: str | None
    created_epoch: int
    locked: list[str]
    central_galaxy_id: int | None = None


class GalaxyRecord(ApiModel):
    id: int
    name: str
    galaxy_type: GalaxyType
    cluster_id: int | None
    dimension_id: int | None
    x: float
    y: float
    radius: float
    arm_count: int
    nucleus: GalacticNucleus
    star_formation: int
    metallicity: int
    age_stage: GalaxyAge
    leak: int
    discovery: Discovery
    patron_son_id: int | None
    merging_with_galaxy_id: int | None
    merge_progress: int
    description: str | None
    image_prompt: str | None
    created_epoch: int
    locked: list[str]


class StructureRecord(ApiModel):
    id: int
    galaxy_id: int
    kind: GalacticStructureKind
    name: str
    x: float
    y: float
    radius: float
    intensity: int
    created_epoch: int
    ended_epoch: int | None
    locked: list[str]


class GalacticEventRecord(ApiModel):
    id: int
    kind: GalacticEventKind
    galaxy_id: int
    other_galaxy_id: int | None
    structure_id: int | None
    star_id: int | None
    epoch: int
    until_epoch: int | None
    intensity: int
    caused_by_node_id: int | None
    text: str | None
    active: bool = False


class DimensionalEventRecord(ApiModel):
    id: int
    kind: DimensionalEventKind
    dimension_id: int
    other_dimension_id: int | None
    world_id: int | None
    region_entity_id: int | None
    subject_entity_id: int | None
    epoch: int
    until_epoch: int | None
    intensity: int
    caused_by_node_id: int | None
    text: str | None
    active: bool = False


class RiftRecord(ApiModel):
    id: int
    world_id: int
    region_entity_id: int | None
    dimension_id: int
    target_world_id: int | None
    size: int
    stability: int
    state: RiftState
    cause: RiftCause
    opened_by_node_id: int | None
    opened_epoch: int
    sealed_epoch: int | None
    route_id: int | None
    locked: list[str]


class CosmicBeingRecord(ApiModel):
    entity_id: int
    name: str = ""
    world_id: int | None = None
    being_kind: BeingKind
    home_dimension_id: int | None
    galaxy_id: int | None
    scale: BeingScale
    might: int
    phase: BeingPhase
    agenda: BeingAgenda
    bound_by_node_id: int | None
    rift_id: int | None
    target_world_id: int | None
    mirrored_entity_id: int | None
    manifest_epochs: int
    locked: list[str]


class FootprintRecord(ApiModel):
    region_entity_id: int
    intensity: int


class PhenomenonRecord(ApiModel):
    entity_id: int
    name: str = ""
    world_id: int | None = None
    kind: PhenomenonKind
    intensity: int
    growth: int
    containment: int
    cause: PhenomenonCause
    cause_node_id: int | None
    formed_epoch: int
    locked: list[str]
    footprints: list[FootprintRecord] = Field(default_factory=list)


class CelestialReadingRecord(ApiModel):
    celestial_entity_id: int
    people_entity_id: int
    reading: OmenReading
    epoch: int
    locked: list[str]


class PullRecord(ApiModel):
    time: float
    capacity: float
    ore: float
    density: float
    magic: int
    leak: int
    sanity: int
    danger: int
    hostility: int


class PlacementRecord(ApiModel):
    world_id: int
    dimension_id: int | None
    cluster_id: int | None
    top_cluster_id: int | None
    galaxy_id: int | None
    structure_id: int | None
    star_id: int | None
    zone: GalacticZone
    pull: PullRecord


class KindRecord(ApiModel):
    value: str
    label: str
    description: str
    effects: dict[str, int] = Field(default_factory=dict)


class GalaxyShapeRecord(ApiModel):
    core_reach_pct: int
    bulge_reach_pct: int
    bar_reach_pct: int
    inner_reach_pct: int
    disc_reach_pct: int
    halo_reach_pct: int
    arm_width_deg: int
    arm_wind_deg: int
    barred_types: list[GalaxyType]
    spiral_types: list[GalaxyType]


class HeldLawRecord(ApiModel):
    law: NaturalLaw
    label: str
    description: str
    entity_id: int | None
    name: str | None
    strength: int


class HostedStratumRecord(ApiModel):
    id: int
    name: str
    kind: StratumKind
    population: int
    realm: NodeRef | None


class ScaleWiki(ApiModel):
    node_id: int
    kind: NodeKind
    depth: EntityDepth | None = None
    cover: str | None
    images: list[ImageRecord]
    timeline: list[ChronicleLineRecord]
    laws: list[HeldLawRecord] = Field(default_factory=list)
    strata: list[HostedStratumRecord] = Field(default_factory=list)


class CosmographyCatalog(ApiModel):
    galaxy_types: list[KindRecord]
    cluster_kinds: list[KindRecord]
    dimension_kinds: list[KindRecord]
    structure_kinds: list[KindRecord]
    zones: list[KindRecord]
    phenomenon_kinds: list[KindRecord]
    being_kinds: list[KindRecord]
    galactic_events: list[KindRecord]
    dimensional_events: list[KindRecord]
    apocalypse_variants: list[KindRecord]
    method_reach: dict[str, RouteScope]
    shape: GalaxyShapeRecord


class CosmographyView(ApiModel):
    epoch: int
    dimensions: list[DimensionRecord]
    clusters: list[ClusterRecord]
    galaxies: list[GalaxyRecord]
    structures: list[StructureRecord]
    galactic_events: list[GalacticEventRecord]
    dimensional_events: list[DimensionalEventRecord]
    rifts: list[RiftRecord]
    beings: list[CosmicBeingRecord]
    phenomena: list[PhenomenonRecord]
    readings: list[CelestialReadingRecord]
    placements: list[PlacementRecord]
    world_names: dict[str, str]
    star_names: dict[str, str]
    people_names: dict[str, str]
    rulers: dict[str, NodeRef] = Field(default_factory=dict)
    actor_names: dict[str, str] = Field(default_factory=dict)
    stars: list[StarRecord]
    apocalypse_variant: ApocalypseVariant | None
    likely_variant: ApocalypseVariant


class SkyWorshipperRecord(ApiModel):
    id: int
    name: str
    entity_type: EntityType
    world_id: int | None
    piety: int | None


class SkyWorshipView(ApiModel):
    node_id: int
    sky: SkyObject
    name: str
    worshippers: list[SkyWorshipperRecord]
    candidates: list[SkyWorshipperRecord]
