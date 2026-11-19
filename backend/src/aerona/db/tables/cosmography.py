from types import MappingProxyType

from sqlalchemy import JSON, CheckConstraint, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.db.tables.node import NodeRow
from aerona.db.types import PydanticJSON
from aerona.domain.enums.cosmography import (
    BeingAgenda,
    BeingKind,
    BeingPhase,
    BeingScale,
    Causality,
    ClusterKind,
    DimensionalEventKind,
    DimensionKind,
    GalacticEventKind,
    GalacticNucleus,
    GalacticStructureKind,
    GalaxyAge,
    GalaxyType,
    OmenReading,
    PhenomenonCause,
    PhenomenonKind,
    RiftCause,
    RiftState,
)
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.world import Discovery
from aerona.domain.models.profiles import EntityDepth


class DimensionRow(NodeRow):
    __tablename__ = "dimensions"
    __table_args__ = (
        between("veil", PERCENT_MIN, PERCENT_MAX),
        between("stability", PERCENT_MIN, PERCENT_MAX),
        between("magic", PERCENT_MIN, PERCENT_MAX),
        between("hostility", PERCENT_MIN, PERCENT_MAX),
        between("leak", PERCENT_MIN, PERCENT_MAX),
        at_least("sanity_drain", 0),
        CheckConstraint("time_factor > 0", name="time_factor_positive"),
        CheckConstraint("parent_dimension_id IS NULL OR parent_dimension_id <> id", name="not_own_parent"),
    )
    __mapper_args__ = MappingProxyType({"polymorphic_identity": NodeKind.DIMENSION, "polymorphic_load": "inline"})

    id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    dimension_kind: Mapped[DimensionKind] = mapped_column(enum_type(DimensionKind, "dimension_kind"))
    parent_dimension_id: Mapped[int | None] = mapped_column(ForeignKey("dimensions.id", ondelete="SET NULL"), index=True)
    veil: Mapped[int] = mapped_column(default=80)
    stability: Mapped[int] = mapped_column(default=80)
    time_factor: Mapped[float] = mapped_column(Float, default=1.0)
    magic: Mapped[int] = mapped_column(default=0)
    hostility: Mapped[int] = mapped_column(default=0)
    sanity_drain: Mapped[int] = mapped_column(default=0)
    leak: Mapped[int] = mapped_column(default=0)
    causality: Mapped[Causality] = mapped_column(enum_type(Causality, "causality"), default=Causality.STRICT)
    discovery: Mapped[Discovery] = mapped_column(enum_type(Discovery, "discovery"), default=Discovery.KNOWN)
    ruler_node_id: Mapped[int | None] = mapped_column(index=True)
    description: Mapped[str | None] = mapped_column(Text)
    image_prompt: Mapped[str | None] = mapped_column(Text)
    depth: Mapped[EntityDepth | None] = mapped_column(PydanticJSON(EntityDepth))
    created_epoch: Mapped[int]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ClusterRow(NodeRow):
    __tablename__ = "galaxy_clusters"
    __table_args__ = (
        between("medium_heat", PERCENT_MIN, PERCENT_MAX),
        between("expansion", PERCENT_MIN, PERCENT_MAX),
        CheckConstraint("radius > 0", name="radius_positive"),
        CheckConstraint("parent_cluster_id IS NULL OR dimension_id IS NULL", name="one_place"),
        CheckConstraint("parent_cluster_id IS NULL OR parent_cluster_id <> id", name="not_own_parent"),
    )
    __mapper_args__ = MappingProxyType({"polymorphic_identity": NodeKind.CLUSTER, "polymorphic_load": "inline"})

    id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    cluster_kind: Mapped[ClusterKind] = mapped_column(enum_type(ClusterKind, "cluster_kind"))
    parent_cluster_id: Mapped[int | None] = mapped_column(ForeignKey("galaxy_clusters.id", ondelete="SET NULL"), index=True)
    dimension_id: Mapped[int | None] = mapped_column(ForeignKey("dimensions.id", ondelete="SET NULL"), index=True)
    x: Mapped[float] = mapped_column(Float, default=0.0)
    y: Mapped[float] = mapped_column(Float, default=0.0)
    radius: Mapped[float] = mapped_column(Float, default=100.0)
    medium_heat: Mapped[int] = mapped_column(default=10)
    expansion: Mapped[int] = mapped_column(default=0)
    discovery: Mapped[Discovery] = mapped_column(enum_type(Discovery, "discovery"), default=Discovery.KNOWN)
    description: Mapped[str | None] = mapped_column(Text)
    image_prompt: Mapped[str | None] = mapped_column(Text)
    depth: Mapped[EntityDepth | None] = mapped_column(PydanticJSON(EntityDepth))
    created_epoch: Mapped[int]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class GalaxyRow(NodeRow):
    __tablename__ = "galaxies"
    __table_args__ = (
        between("star_formation", PERCENT_MIN, PERCENT_MAX),
        between("metallicity", PERCENT_MIN, PERCENT_MAX),
        between("leak", PERCENT_MIN, PERCENT_MAX),
        between("merge_progress", PERCENT_MIN, PERCENT_MAX),
        at_least("arm_count", 0),
        CheckConstraint("radius > 0", name="radius_positive"),
        CheckConstraint("cluster_id IS NULL OR dimension_id IS NULL", name="one_place"),
        CheckConstraint("merging_with_galaxy_id IS NULL OR merging_with_galaxy_id <> id", name="not_own_merger"),
    )
    __mapper_args__ = MappingProxyType({"polymorphic_identity": NodeKind.GALAXY, "polymorphic_load": "inline"})

    id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    galaxy_type: Mapped[GalaxyType] = mapped_column(enum_type(GalaxyType, "galaxy_type"))
    cluster_id: Mapped[int | None] = mapped_column(ForeignKey("galaxy_clusters.id", ondelete="SET NULL"), index=True)
    dimension_id: Mapped[int | None] = mapped_column(ForeignKey("dimensions.id", ondelete="SET NULL"), index=True)
    x: Mapped[float] = mapped_column(Float, default=0.0)
    y: Mapped[float] = mapped_column(Float, default=0.0)
    radius: Mapped[float] = mapped_column(Float, default=100.0)
    arm_count: Mapped[int] = mapped_column(default=2)
    nucleus: Mapped[GalacticNucleus] = mapped_column(enum_type(GalacticNucleus, "nucleus"), default=GalacticNucleus.DORMANT)
    star_formation: Mapped[int] = mapped_column(default=30)
    metallicity: Mapped[int] = mapped_column(default=50)
    age_stage: Mapped[GalaxyAge] = mapped_column(enum_type(GalaxyAge, "age_stage"), default=GalaxyAge.MATURE)
    leak: Mapped[int] = mapped_column(default=0)
    discovery: Mapped[Discovery] = mapped_column(enum_type(Discovery, "discovery"), default=Discovery.KNOWN)
    patron_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL", use_alter=True), index=True)
    merging_with_galaxy_id: Mapped[int | None] = mapped_column(ForeignKey("galaxies.id", ondelete="SET NULL"))
    merge_progress: Mapped[int] = mapped_column(default=0)
    description: Mapped[str | None] = mapped_column(Text)
    image_prompt: Mapped[str | None] = mapped_column(Text)
    depth: Mapped[EntityDepth | None] = mapped_column(PydanticJSON(EntityDepth))
    created_epoch: Mapped[int]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class GalacticStructureRow(Base):
    __tablename__ = "galactic_structures"
    __table_args__ = (
        between("intensity", PERCENT_MIN, PERCENT_MAX),
        CheckConstraint("radius > 0", name="radius_positive"),
        CheckConstraint("ended_epoch IS NULL OR ended_epoch >= created_epoch", name="ends_after_start"),
        Index("ix_galactic_structures_galaxy", "galaxy_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    galaxy_id: Mapped[int] = mapped_column(ForeignKey("galaxies.id", ondelete="CASCADE"))
    kind: Mapped[GalacticStructureKind] = mapped_column(enum_type(GalacticStructureKind, "kind"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    x: Mapped[float] = mapped_column(Float, default=0.0)
    y: Mapped[float] = mapped_column(Float, default=0.0)
    radius: Mapped[float] = mapped_column(Float, default=10.0)
    intensity: Mapped[int] = mapped_column(default=50)
    created_epoch: Mapped[int]
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class GalacticEventRow(Base):
    __tablename__ = "galactic_events"
    __table_args__ = (
        between("intensity", PERCENT_MIN, PERCENT_MAX),
        at_least("epoch", 1),
        CheckConstraint("until_epoch IS NULL OR until_epoch >= epoch", name="until_after_start"),
        Index("ix_galactic_events_galaxy_epoch", "galaxy_id", "epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[GalacticEventKind] = mapped_column(enum_type(GalacticEventKind, "kind"))
    galaxy_id: Mapped[int] = mapped_column(ForeignKey("galaxies.id", ondelete="CASCADE"))
    other_galaxy_id: Mapped[int | None] = mapped_column(ForeignKey("galaxies.id", ondelete="SET NULL"))
    structure_id: Mapped[int | None] = mapped_column(ForeignKey("galactic_structures.id", ondelete="SET NULL"))
    star_id: Mapped[int | None] = mapped_column(ForeignKey("stars.id", ondelete="SET NULL"))
    epoch: Mapped[int]
    until_epoch: Mapped[int | None]
    intensity: Mapped[int] = mapped_column(default=50)
    caused_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    text: Mapped[str | None] = mapped_column(Text)


class DimensionalEventRow(Base):
    __tablename__ = "dimensional_events"
    __table_args__ = (
        between("intensity", PERCENT_MIN, PERCENT_MAX),
        at_least("epoch", 1),
        CheckConstraint("until_epoch IS NULL OR until_epoch >= epoch", name="until_after_start"),
        CheckConstraint("other_dimension_id IS NULL OR other_dimension_id <> dimension_id", name="two_dimensions"),
        Index("ix_dimensional_events_dimension_epoch", "dimension_id", "epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[DimensionalEventKind] = mapped_column(enum_type(DimensionalEventKind, "kind"))
    dimension_id: Mapped[int] = mapped_column(ForeignKey("dimensions.id", ondelete="CASCADE"))
    other_dimension_id: Mapped[int | None] = mapped_column(ForeignKey("dimensions.id", ondelete="SET NULL"))
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    region_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    subject_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    epoch: Mapped[int]
    until_epoch: Mapped[int | None]
    intensity: Mapped[int] = mapped_column(default=50)
    caused_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    text: Mapped[str | None] = mapped_column(Text)


class RiftRow(Base):
    __tablename__ = "rifts"
    __table_args__ = (
        between("size", PERCENT_MIN, PERCENT_MAX),
        between("stability", PERCENT_MIN, PERCENT_MAX),
        at_least("opened_epoch", 1),
        CheckConstraint("sealed_epoch IS NULL OR sealed_epoch >= opened_epoch", name="sealed_after_open"),
        CheckConstraint("target_world_id IS NULL OR target_world_id <> world_id", name="two_worlds"),
        Index("ix_rifts_world_state", "world_id", "state"),
        Index("ix_rifts_dimension", "dimension_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    region_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    dimension_id: Mapped[int] = mapped_column(ForeignKey("dimensions.id", ondelete="CASCADE"))
    target_world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    size: Mapped[int] = mapped_column(default=20)
    stability: Mapped[int] = mapped_column(default=50)
    state: Mapped[RiftState] = mapped_column(enum_type(RiftState, "state"), default=RiftState.OPENING)
    cause: Mapped[RiftCause] = mapped_column(enum_type(RiftCause, "cause"))
    opened_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    opened_epoch: Mapped[int]
    sealed_epoch: Mapped[int | None]
    route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PhenomenonProfileRow(Base):
    __tablename__ = "phenomenon_profiles"
    __table_args__ = (
        between("intensity", PERCENT_MIN, PERCENT_MAX),
        between("containment", PERCENT_MIN, PERCENT_MAX),
        between("growth", -PERCENT_MAX, PERCENT_MAX),
        at_least("formed_epoch", 1),
    )

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[PhenomenonKind] = mapped_column(enum_type(PhenomenonKind, "kind"), index=True)
    intensity: Mapped[int] = mapped_column(default=50)
    growth: Mapped[int] = mapped_column(default=5)
    containment: Mapped[int] = mapped_column(default=0)
    cause: Mapped[PhenomenonCause] = mapped_column(enum_type(PhenomenonCause, "cause"))
    cause_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    formed_epoch: Mapped[int]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PhenomenonFootprintRow(Base):
    __tablename__ = "phenomenon_footprints"
    __table_args__ = (between("intensity", PERCENT_MIN, PERCENT_MAX), Index("ix_phenomenon_footprints_region", "region_entity_id"))

    phenomenon_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    intensity: Mapped[int] = mapped_column(default=50)


class CosmicBeingProfileRow(Base):
    __tablename__ = "cosmic_being_profiles"
    __table_args__ = (between("might", PERCENT_MIN, PERCENT_MAX), at_least("manifest_epochs", 0))

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    being_kind: Mapped[BeingKind] = mapped_column(enum_type(BeingKind, "being_kind"), index=True)
    home_dimension_id: Mapped[int | None] = mapped_column(ForeignKey("dimensions.id", ondelete="SET NULL"), index=True)
    galaxy_id: Mapped[int | None] = mapped_column(ForeignKey("galaxies.id", ondelete="SET NULL"), index=True)
    scale: Mapped[BeingScale] = mapped_column(enum_type(BeingScale, "scale"), default=BeingScale.WORLD)
    might: Mapped[int] = mapped_column(default=50)
    phase: Mapped[BeingPhase] = mapped_column(enum_type(BeingPhase, "phase"), default=BeingPhase.ROAMING)
    agenda: Mapped[BeingAgenda] = mapped_column(enum_type(BeingAgenda, "agenda"), default=BeingAgenda.EXPLORE)
    bound_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    rift_id: Mapped[int | None] = mapped_column(ForeignKey("rifts.id", ondelete="SET NULL"))
    target_world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    mirrored_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    manifest_epochs: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CelestialReadingRow(Base):
    __tablename__ = "celestial_readings"
    __table_args__ = (at_least("epoch", 1), Index("ix_celestial_readings_people", "people_entity_id"))

    celestial_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    reading: Mapped[OmenReading] = mapped_column(enum_type(OmenReading, "reading"))
    visible: Mapped[bool] = mapped_column(default=True, server_default="1")
    epoch: Mapped[int]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
