from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH, SHORT_TEXT_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.db.profile_guard import register_profile_table
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.ecology import (
    BeastTemper,
    Biochemistry,
    Diet,
    DomesticationStage,
    HerdTraining,
    RangeTrend,
    SizeClass,
    Sociality,
    SpeciesClass,
    SpeciesUse,
)
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.material import MaterialKind


class SpeciesProfileRow(Base):
    __tablename__ = "species_profiles"
    __table_args__ = (
        between("aggression", PERCENT_MIN, PERCENT_MAX),
        between("territoriality", PERCENT_MIN, PERCENT_MAX),
        between("cunning", PERCENT_MIN, PERCENT_MAX),
        between("fear_of_people", PERCENT_MIN, PERCENT_MAX),
        between("tameability", PERCENT_MIN, PERCENT_MAX),
        between("water_need", PERCENT_MIN, PERCENT_MAX),
        between("metabolism", PERCENT_MIN, PERCENT_MAX),
        at_least("lifespan_years", 1),
        at_least("maturity_years", 0),
        at_least("litter_size", 1),
        at_least("breeding_seasons", 0),
    )

    species_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    species_class: Mapped[SpeciesClass] = mapped_column(enum_type(SpeciesClass, "species_class"), default=SpeciesClass.ANIMAL)
    biochemistry: Mapped[Biochemistry] = mapped_column(enum_type(Biochemistry, "biochemistry"), default=Biochemistry.CARBON_WATER)
    body_plan: Mapped[BodyPlan] = mapped_column(enum_type(BodyPlan, "body_plan"), default=BodyPlan.QUADRUPED)
    size_class: Mapped[SizeClass] = mapped_column(enum_type(SizeClass, "size_class"), default=SizeClass.MEDIUM)
    lifespan_years: Mapped[int] = mapped_column(default=10)
    maturity_years: Mapped[int] = mapped_column(default=1)
    litter_size: Mapped[int] = mapped_column(default=2)
    breeding_seasons: Mapped[int] = mapped_column(default=1)
    diet: Mapped[Diet] = mapped_column(enum_type(Diet, "diet"), default=Diet.HERBIVORE)
    metabolism: Mapped[int] = mapped_column(default=50)
    habitat: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    temperature_min: Mapped[int] = mapped_column(default=-10)
    temperature_max: Mapped[int] = mapped_column(default=35)
    water_need: Mapped[int] = mapped_column(default=50)
    altitude_min: Mapped[int] = mapped_column(default=0)
    altitude_max: Mapped[int] = mapped_column(default=3000)
    nocturnal: Mapped[bool] = mapped_column(default=False)
    migratory: Mapped[bool] = mapped_column(default=False)
    migration_path: Mapped[list[int]] = mapped_column(JSON, default=list)
    aggression: Mapped[int] = mapped_column(default=30)
    territoriality: Mapped[int] = mapped_column(default=30)
    sociality: Mapped[Sociality] = mapped_column(enum_type(Sociality, "sociality"), default=Sociality.HERD)
    cunning: Mapped[int] = mapped_column(default=30)
    fear_of_people: Mapped[int] = mapped_column(default=50)
    tameability: Mapped[int] = mapped_column(default=20)
    stage: Mapped[DomesticationStage] = mapped_column(enum_type(DomesticationStage, "stage"), default=DomesticationStage.WILD)
    domesticated_from_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    sacred_to_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    stage_epoch: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    pinned_prey: Mapped[list[int]] = mapped_column(JSON, default=list)
    barred_prey: Mapped[list[int]] = mapped_column(JSON, default=list)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SpeciesRangeRow(Base):
    __tablename__ = "species_ranges"
    __table_args__ = (at_least("abundance", 0), Index("ix_species_ranges_region", "region_entity_id"))

    species_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    abundance: Mapped[int] = mapped_column(default=0)
    trend: Mapped[RangeTrend] = mapped_column(enum_type(RangeTrend, "trend"), default=RangeTrend.STEADY)
    fit: Mapped[int] = mapped_column(default=50)
    hunted: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SpeciesYieldRow(Base):
    __tablename__ = "species_yields"
    __table_args__ = (at_least("rate", 0),)

    species_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    product: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH), primary_key=True)
    commodity: Mapped[CommodityKind | None] = mapped_column(enum_type(CommodityKind, "commodity"))
    material: Mapped[MaterialKind | None] = mapped_column(enum_type(MaterialKind, "material"))
    world_material_id: Mapped[int | None] = mapped_column(ForeignKey("world_materials.id", ondelete="SET NULL"))
    rate: Mapped[int] = mapped_column(default=1)


class SpeciesUseRow(Base):
    __tablename__ = "species_uses"

    species_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    use: Mapped[SpeciesUse] = mapped_column(enum_type(SpeciesUse, "use"), primary_key=True)


class SpeciesUseKindRow(Base):
    __tablename__ = "species_use_kinds"
    __table_args__ = (between("output_pct", 0, 1000),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    base_use: Mapped[SpeciesUse] = mapped_column(enum_type(SpeciesUse, "base_use"))
    output_pct: Mapped[int] = mapped_column(default=100)
    description: Mapped[str | None] = mapped_column(String(SHORT_TEXT_MAX_LENGTH))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SpeciesCustomUseRow(Base):
    __tablename__ = "species_custom_uses"
    __table_args__ = (Index("ix_species_custom_uses_kind", "kind_id"),)

    species_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind_id: Mapped[int] = mapped_column(ForeignKey("species_use_kinds.id", ondelete="CASCADE"), primary_key=True)


class SpeciesHostRow(Base):
    __tablename__ = "species_hosts"

    species_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    disease_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    immune: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class HerdRow(Base):
    __tablename__ = "herds"
    __table_args__ = (at_least("head", 0), Index("ix_herds_species", "species_entity_id"))

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    species_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    head: Mapped[int] = mapped_column(default=0)
    stage: Mapped[DomesticationStage] = mapped_column(enum_type(DomesticationStage, "stage"), default=DomesticationStage.TAMED)
    since_epoch: Mapped[int] = mapped_column(default=0)
    fed_epochs: Mapped[int] = mapped_column(default=0)
    training: Mapped[HerdTraining | None] = mapped_column(enum_type(HerdTraining, "training"))
    trained: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class BeastProfileRow(Base):
    __tablename__ = "beast_profiles"
    __table_args__ = (
        between("endurance", PERCENT_MIN, PERCENT_MAX),
        between("perception", PERCENT_MIN, PERCENT_MAX),
        between("willpower", PERCENT_MIN, PERCENT_MAX),
        between("intelligence", PERCENT_MIN, PERCENT_MAX),
        at_least("age", 0),
        at_least("lifespan", 1),
        Index("ix_beast_profiles_species", "species_entity_id"),
    )

    beast_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    species_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    endurance: Mapped[int] = mapped_column(default=50)
    perception: Mapped[int] = mapped_column(default=50)
    willpower: Mapped[int] = mapped_column(default=50)
    intelligence: Mapped[int] = mapped_column(default=20)
    age: Mapped[int] = mapped_column(default=0)
    lifespan: Mapped[int] = mapped_column(default=100)
    size_class: Mapped[SizeClass] = mapped_column(enum_type(SizeClass, "size_class"), default=SizeClass.HUGE)
    lair_place_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    temper: Mapped[BeastTemper] = mapped_column(enum_type(BeastTemper, "temper"), default=BeastTemper.SLEEPING)
    bound_to_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    hoard: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    raids: Mapped[int] = mapped_column(default=0)
    woke_epoch: Mapped[int | None]
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


register_profile_table(SpeciesRangeRow.__tablename__, "species_entity_id")
register_profile_table(HerdRow.__tablename__, "community_entity_id")
register_profile_table(SpeciesHostRow.__tablename__, "species_entity_id")
