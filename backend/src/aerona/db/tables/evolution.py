from sqlalchemy import JSON, Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.evolution import EvolvedTrait, KeystoneRole, PlagueResponse, TrophicLevel
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

TRAIT_FIELDS = ("mean", "variance")
MARK_FIELDS = ("blessing", "source_node_id")
CARRIER_FIELDS = ("identified", "seeded")
RESPONSE_FIELDS = ("until_epoch", "strength")
RESEARCH_FIELDS = ("points", "specimens")
CYCLE_FIELDS = ("carbon", "water", "nutrients")
SERVICE_FIELDS = ("strength", "species_entity_id")


class SpeciesTraitRow(Base):
    __tablename__ = "species_traits"
    __table_args__ = (between("mean", PERCENT_MIN, PERCENT_MAX), between("variance", 0, 50), Index("ix_species_traits_region", "region_entity_id"))

    species_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    trait: Mapped[EvolvedTrait] = mapped_column(enum_type(EvolvedTrait, "trait"), primary_key=True)
    mean: Mapped[int] = mapped_column(default=50)
    variance: Mapped[int] = mapped_column(default=10)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LineageMarkRow(Base):
    __tablename__ = "lineage_marks"
    __table_args__ = (at_least("epoch", 0),)

    species_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    package: Mapped[PackageKind] = mapped_column(enum_type(PackageKind, "package"), primary_key=True)
    blessing: Mapped[bool] = mapped_column(Boolean, default=False)
    source_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TrophicLevelRow(Base):
    __tablename__ = "trophic_levels"
    __table_args__ = (at_least("biomass", 0), at_least("cap", 0))

    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    level: Mapped[TrophicLevel] = mapped_column(enum_type(TrophicLevel, "level"), primary_key=True)
    biomass: Mapped[int] = mapped_column(default=0)
    cap: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)


class EcosystemServiceRow(Base):
    __tablename__ = "ecosystem_services"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX),)

    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[KeystoneRole] = mapped_column(enum_type(KeystoneRole, "role"), primary_key=True)
    species_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    strength: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CarrierRow(Base):
    __tablename__ = "disease_carriers"
    __table_args__ = (at_least("since_epoch", 0), Index("ix_disease_carriers_disease", "disease_entity_id"))

    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    disease_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    home_region_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    identified: Mapped[bool] = mapped_column(Boolean, default=False)
    seeded: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PlagueResponseRow(Base):
    __tablename__ = "plague_responses"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX), at_least("since_epoch", 0))

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    disease_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    response: Mapped[PlagueResponse] = mapped_column(enum_type(PlagueResponse, "response"), primary_key=True)
    strength: Mapped[int] = mapped_column(default=60)
    since_epoch: Mapped[int] = mapped_column(default=0)
    until_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CureResearchRow(Base):
    __tablename__ = "cure_research"
    __table_args__ = (at_least("points", 0), at_least("specimens", 0), at_least("started_epoch", 0))

    institution_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    disease_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    points: Mapped[int] = mapped_column(default=0)
    specimens: Mapped[int] = mapped_column(default=0)
    started_epoch: Mapped[int] = mapped_column(default=0)
    cured_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class WorldCycleRow(Base):
    __tablename__ = "world_cycles"
    __table_args__ = (between("carbon", PERCENT_MIN, PERCENT_MAX), between("water", PERCENT_MIN, PERCENT_MAX), between("nutrients", PERCENT_MIN, PERCENT_MAX))

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    carbon: Mapped[int] = mapped_column(default=50)
    water: Mapped[int] = mapped_column(default=50)
    nutrients: Mapped[int] = mapped_column(default=50)
    carbon_in: Mapped[int] = mapped_column(default=0)
    carbon_out: Mapped[int] = mapped_column(default=0)
    water_in: Mapped[int] = mapped_column(default=0)
    water_out: Mapped[int] = mapped_column(default=0)
    nutrients_in: Mapped[int] = mapped_column(default=0)
    nutrients_out: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TraitHistoryRow(Base):
    __tablename__ = "trait_history"
    __table_args__ = (at_least("epoch", 0),)

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    trait: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH), primary_key=True)
    epoch: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[int] = mapped_column(default=0)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"), index=True)
