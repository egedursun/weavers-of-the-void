from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.demography import AgeBand
from aerona.domain.enums.disease import ClimateAffinity, CureSource, DiseaseVector, OutbreakStatus, SpreadPath
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN


class DiseaseProfileRow(Base):
    __tablename__ = "disease_profiles"
    __table_args__ = (
        between("virulence", PERCENT_MIN, PERCENT_MAX),
        between("lethality", PERCENT_MIN, PERCENT_MAX),
        between("chronic_rate", PERCENT_MIN, PERCENT_MAX),
        between("mutation_rate", PERCENT_MIN, PERCENT_MAX),
        between("stigma", PERCENT_MIN, PERCENT_MAX),
        at_least("incubation", 0),
        at_least("immunity_epochs", 1),
        at_least("cure_level", 0),
        at_least("generation", 0),
    )

    disease_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    vector: Mapped[DiseaseVector] = mapped_column(enum_type(DiseaseVector, "vector"))
    virulence: Mapped[int]
    lethality: Mapped[int]
    chronic_rate: Mapped[int]
    incubation: Mapped[int]
    target_functions: Mapped[list[str]] = mapped_column(JSON, default=list)
    climate_affinity: Mapped[ClimateAffinity] = mapped_column(enum_type(ClimateAffinity, "climate_affinity"))
    host_species_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    immunity_epochs: Mapped[int]
    mutation_rate: Mapped[int]
    origin_incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    origin_region_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    parent_disease_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    generation: Mapped[int] = mapped_column(default=0)
    stigma: Mapped[int]
    cure_level: Mapped[int]
    emerged_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class OutbreakRow(Base):
    __tablename__ = "outbreaks"
    __table_args__ = (
        at_least("infected", 0),
        at_least("dead", 0),
        at_least("started_epoch", 0),
        between("severity", PERCENT_MIN, PERCENT_MAX),
        at_least("season_factor", 0),
        Index("ix_outbreaks_disease", "disease_entity_id", "status"),
        Index("ix_outbreaks_region", "region_entity_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    disease_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    event_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    source_outbreak_id: Mapped[int | None] = mapped_column(ForeignKey("outbreaks.id", ondelete="SET NULL"))
    path: Mapped[SpreadPath] = mapped_column(enum_type(SpreadPath, "path"))
    status: Mapped[OutbreakStatus] = mapped_column(enum_type(OutbreakStatus, "status"), default=OutbreakStatus.ACTIVE)
    severity: Mapped[int]
    infected: Mapped[int] = mapped_column(default=0)
    dead: Mapped[int] = mapped_column(default=0)
    started_epoch: Mapped[int]
    ended_epoch: Mapped[int | None]
    quarantined: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
    season_factor: Mapped[int] = mapped_column(default=100)


class ImmunityRow(Base):
    __tablename__ = "immunities"
    __table_args__ = (between("immune_pct", PERCENT_MIN, PERCENT_MAX), Index("ix_immunities_disease", "disease_entity_id"))

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    disease_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    age_band: Mapped[AgeBand] = mapped_column(enum_type(AgeBand, "age_band"), primary_key=True)
    immune_pct: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[bool] = mapped_column(default=False)


class EndemicDiseaseRow(Base):
    __tablename__ = "endemic_diseases"
    __table_args__ = (between("load", PERCENT_MIN, PERCENT_MAX), Index("ix_endemic_diseases_disease", "disease_entity_id"))

    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    disease_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    load: Mapped[int]
    since_epoch: Mapped[int]
    locked: Mapped[bool] = mapped_column(default=False)


class DiseaseCureRow(Base):
    __tablename__ = "disease_cures"

    disease_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    source: Mapped[CureSource] = mapped_column(enum_type(CureSource, "source"))
    since_epoch: Mapped[int]


class QuarantineRow(Base):
    __tablename__ = "quarantines"
    __table_args__ = (at_least("started_epoch", 0),)

    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    started_epoch: Mapped[int]
    until_epoch: Mapped[int]
    ordered_by_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    ordered_by_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
