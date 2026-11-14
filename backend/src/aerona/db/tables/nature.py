from sqlalchemy import JSON, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.nature import FermentKind, SenseKind, SymbiosisKind

MICROBIOTA_FIELDS = ("life", "sterile_epochs")
CULTURE_FIELDS = ("holder_entity_id", "kind", "quality", "lost_epoch")
RELATION_FIELDS = ("first_species_id", "second_species_id", "kind", "strength")
SENSE_FIELDS = ("acuity",)


class SoilMicrobiotaRow(Base):
    __tablename__ = "soil_microbiota"
    __table_args__ = (between("life", PERCENT_MIN, PERCENT_MAX), at_least("sterile_epochs", 0), at_least("updated_epoch", 0))

    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    life: Mapped[int] = mapped_column(default=50)
    sterile_epochs: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class FermentCultureRow(Base):
    __tablename__ = "ferment_cultures"
    __table_args__ = (between("quality", PERCENT_MIN, PERCENT_MAX), at_least("since_epoch", 0), Index("ix_ferment_cultures_holder", "holder_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[FermentKind] = mapped_column(enum_type(FermentKind, "kind"))
    quality: Mapped[int] = mapped_column(default=30)
    since_epoch: Mapped[int] = mapped_column(default=0)
    lost_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SpeciesRelationRow(Base):
    __tablename__ = "species_relations"
    __table_args__ = (
        between("strength", PERCENT_MIN, PERCENT_MAX),
        at_least("since_epoch", 0),
        UniqueConstraint("first_species_id", "second_species_id", "kind", name="uq_species_relations_pair"),
        Index("ix_species_relations_second", "second_species_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    first_species_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    second_species_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[SymbiosisKind] = mapped_column(enum_type(SymbiosisKind, "kind"))
    strength: Mapped[int] = mapped_column(default=40)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SenseProfileRow(Base):
    __tablename__ = "sense_profiles"
    __table_args__ = (between("acuity", PERCENT_MIN, PERCENT_MAX),)

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    sense: Mapped[SenseKind] = mapped_column(enum_type(SenseKind, "sense"), primary_key=True)
    acuity: Mapped[int] = mapped_column(default=50)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
