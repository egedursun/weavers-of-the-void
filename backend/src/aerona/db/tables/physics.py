from sqlalchemy import JSON, CheckConstraint, Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.physics import (
    CosmicFeatureKind,
    ImpactBody,
    ImpactOutcome,
    LifeComplexity,
    SurveyLevel,
    SystemRole,
    TerraformAim,
)


class StarSystemRow(Base):
    __tablename__ = "star_systems"
    __table_args__ = (
        at_least("created_epoch", 1),
        CheckConstraint("separation >= 0", name="separation_positive"),
        Index("ix_star_systems_galaxy", "galaxy_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    galaxy_id: Mapped[int | None] = mapped_column(ForeignKey("galaxies.id", ondelete="SET NULL"))
    x: Mapped[float] = mapped_column(Float, default=0.0)
    y: Mapped[float] = mapped_column(Float, default=0.0)
    separation: Mapped[float] = mapped_column(Float, default=0.0)
    band_inner: Mapped[float] = mapped_column(Float, default=0.0)
    band_outer: Mapped[float] = mapped_column(Float, default=0.0)
    created_epoch: Mapped[int]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class StarPhysicsRow(Base):
    __tablename__ = "star_physics"
    __table_args__ = (
        CheckConstraint("mass > 0", name="mass_positive"),
        between("metallicity", PERCENT_MIN, PERCENT_MAX),
        at_least("age_epochs", 0),
        at_least("upkeep", 0),
        Index("ix_star_physics_system", "system_id"),
    )

    star_id: Mapped[int] = mapped_column(ForeignKey("stars.id", ondelete="CASCADE"), primary_key=True)
    mass: Mapped[float] = mapped_column(Float, default=1.0)
    metallicity: Mapped[int] = mapped_column(default=50)
    age_epochs: Mapped[int] = mapped_column(default=0)
    system_id: Mapped[int | None] = mapped_column(ForeignKey("star_systems.id", ondelete="SET NULL"))
    role: Mapped[SystemRole] = mapped_column(enum_type(SystemRole, "role"), default=SystemRole.PRIMARY)
    maker_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    upkeep: Mapped[int] = mapped_column(default=0)
    luminosity: Mapped[float] = mapped_column(Float, default=1.0)
    lifetime_epochs: Mapped[int] = mapped_column(default=0)
    band_inner: Mapped[float] = mapped_column(Float, default=0.0)
    band_outer: Mapped[float] = mapped_column(Float, default=0.0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class WorldPhysicsRow(Base):
    __tablename__ = "world_physics"
    __table_args__ = (
        CheckConstraint("eccentricity >= 0 AND eccentricity < 1", name="eccentricity_range"),
        CheckConstraint("mass > 0", name="mass_positive"),
        CheckConstraint("radius > 0", name="radius_positive"),
        CheckConstraint("rotation_hours > 0", name="rotation_positive"),
        CheckConstraint("pressure >= 0", name="pressure_positive"),
        *(
            between(name, PERCENT_MIN, PERCENT_MAX)
            for name in (
                "iron",
                "rock",
                "ice",
                "gas",
                "exotic",
                "nitrogen",
                "oxygen",
                "carbon_dioxide",
                "methane",
                "water_vapour",
                "exotic_gas",
                "albedo",
                "tectonics",
                "volcanism",
                "hydrosphere",
                "cryosphere",
                "aurora",
            )
        ),
    )

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    eccentricity: Mapped[float] = mapped_column(Float, default=0.02)
    inclination: Mapped[float] = mapped_column(Float, default=1.0)
    argument: Mapped[float] = mapped_column(Float, default=0.0)
    mass: Mapped[float] = mapped_column(Float, default=1.0)
    radius: Mapped[float] = mapped_column(Float, default=1.0)
    iron: Mapped[int] = mapped_column(default=30)
    rock: Mapped[int] = mapped_column(default=65)
    ice: Mapped[int] = mapped_column(default=5)
    gas: Mapped[int] = mapped_column(default=0)
    exotic: Mapped[int] = mapped_column(default=0)
    rotation_hours: Mapped[float] = mapped_column(Float, default=24.0)
    nitrogen: Mapped[int] = mapped_column(default=78)
    oxygen: Mapped[int] = mapped_column(default=21)
    carbon_dioxide: Mapped[int] = mapped_column(default=1)
    methane: Mapped[int] = mapped_column(default=0)
    ammonia: Mapped[int] = mapped_column(default=0, server_default="0")
    hydrogen: Mapped[int] = mapped_column(default=0, server_default="0")
    water_vapour: Mapped[int] = mapped_column(default=0)
    exotic_gas: Mapped[int] = mapped_column(default=0)
    pressure: Mapped[float] = mapped_column(Float, default=1.0)
    albedo: Mapped[int] = mapped_column(default=30)
    tectonics: Mapped[int] = mapped_column(default=50)
    volcanism: Mapped[int] = mapped_column(default=20)
    hydrosphere: Mapped[int] = mapped_column(default=60)
    cryosphere: Mapped[int] = mapped_column(default=10)
    circumbinary: Mapped[bool] = mapped_column(default=False)
    insolation: Mapped[float] = mapped_column(Float, default=1.0)
    surface_temperature: Mapped[float] = mapped_column(Float, default=288.0)
    gravity_g: Mapped[float] = mapped_column(Float, default=1.0)
    escape_velocity: Mapped[float] = mapped_column(Float, default=1.0)
    tidally_locked: Mapped[bool] = mapped_column(default=False)
    ringed: Mapped[bool] = mapped_column(default=False)
    aurora: Mapped[int] = mapped_column(default=0)
    eclipse_years: Mapped[int] = mapped_column(default=0)
    heat_shift: Mapped[int] = mapped_column(default=0)
    sea_level: Mapped[int] = mapped_column(default=0)
    habitable: Mapped[bool] = mapped_column(default=True)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class WorldLifeRow(Base):
    __tablename__ = "world_life"

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    complexity: Mapped[LifeComplexity] = mapped_column(enum_type(LifeComplexity, "complexity"), default=LifeComplexity.COMPLEX)
    environments: Mapped[list[str]] = mapped_column(JSON, default=list)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CosmicFeatureRow(Base):
    __tablename__ = "cosmic_features"
    __table_args__ = (
        at_least("created_epoch", 1),
        CheckConstraint("ended_epoch IS NULL OR ended_epoch >= created_epoch", name="ended_after_start"),
        CheckConstraint("radius >= 0", name="radius_positive"),
        at_least("period_epochs", 0),
        *(between(name, PERCENT_MIN, PERCENT_MAX) for name in ("density", "radiation", "omen_weight", "richness", "pirates", "instability")),
        between("travel", -PERCENT_MAX, PERCENT_MAX),
        Index("ix_cosmic_features_star", "star_id"),
        Index("ix_cosmic_features_galaxy", "galaxy_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[CosmicFeatureKind] = mapped_column(enum_type(CosmicFeatureKind, "kind"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    galaxy_id: Mapped[int | None] = mapped_column(ForeignKey("galaxies.id", ondelete="SET NULL"))
    star_id: Mapped[int | None] = mapped_column(ForeignKey("stars.id", ondelete="SET NULL"))
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    world_b_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id", ondelete="SET NULL"))
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    x: Mapped[float] = mapped_column(Float, default=0.0)
    y: Mapped[float] = mapped_column(Float, default=0.0)
    radius: Mapped[float] = mapped_column(Float, default=0.0)
    density: Mapped[int] = mapped_column(default=50)
    radiation: Mapped[int] = mapped_column(default=0)
    travel: Mapped[int] = mapped_column(default=0)
    omen_weight: Mapped[int] = mapped_column(default=0)
    richness: Mapped[int] = mapped_column(default=0)
    pirates: Mapped[int] = mapped_column(default=0)
    instability: Mapped[int] = mapped_column(default=0)
    period_epochs: Mapped[int] = mapped_column(default=0)
    next_return_epoch: Mapped[int | None]
    description: Mapped[str | None] = mapped_column(Text)
    created_epoch: Mapped[int]
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ImpactEventRow(Base):
    __tablename__ = "impact_events"
    __table_args__ = (
        between("size", PERCENT_MIN, PERCENT_MAX),
        at_least("due_epoch", 1),
        at_least("winter_epochs", 0),
        Index("ix_impact_events_world", "world_id", "outcome"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    region_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    feature_id: Mapped[int | None] = mapped_column(ForeignKey("cosmic_features.id", ondelete="SET NULL"))
    fragment_world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    wreck_remnant_id: Mapped[int | None] = mapped_column(ForeignKey("war_remnants.id", ondelete="SET NULL"))
    body: Mapped[ImpactBody] = mapped_column(enum_type(ImpactBody, "body"))
    size: Mapped[int] = mapped_column(default=30)
    due_epoch: Mapped[int]
    warned_epoch: Mapped[int | None]
    outcome: Mapped[ImpactOutcome] = mapped_column(enum_type(ImpactOutcome, "outcome"), default=ImpactOutcome.PENDING)
    crater_place_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    winter_epochs: Mapped[int] = mapped_column(default=0)
    deflected_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    called_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    text: Mapped[str] = mapped_column(Text, default="")
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TerraformingRow(Base):
    __tablename__ = "terraforming"
    __table_args__ = (between("step", 1, PERCENT_MAX), at_least("epochs_left", 0), at_least("started_epoch", 1), Index("ix_terraforming_world", "world_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    aim: Mapped[TerraformAim] = mapped_column(enum_type(TerraformAim, "aim"))
    by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    step: Mapped[int] = mapped_column(default=5)
    epochs_left: Mapped[int] = mapped_column(default=5)
    started_epoch: Mapped[int]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class WorldSurveyRow(Base):
    __tablename__ = "world_surveys"
    __table_args__ = (UniqueConstraint("observer_entity_id", "world_id", name="one_survey"), at_least("epoch", 0), Index("ix_world_surveys_world", "world_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    observer_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    level: Mapped[SurveyLevel] = mapped_column(enum_type(SurveyLevel, "level"), default=SurveyLevel.UNKNOWN)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
