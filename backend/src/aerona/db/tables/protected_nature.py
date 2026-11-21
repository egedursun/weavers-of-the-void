from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.protected_nature import ProtectionBasis


class ProtectedAreaRow(Base):
    __tablename__ = "protected_areas"
    __table_args__ = (
        between("strength", PERCENT_MIN, PERCENT_MAX),
        between("poaching", PERCENT_MIN, PERCENT_MAX),
        at_least("wardens", 0),
        Index("ix_protected_areas_region", "region_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    site_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    protector_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"), index=True)
    basis: Mapped[ProtectionBasis] = mapped_column(enum_type(ProtectionBasis, "basis"), default=ProtectionBasis.LAW)
    banned_uses: Mapped[list[str]] = mapped_column(JSON, default=list)
    wardens: Mapped[int] = mapped_column(default=0)
    strength: Mapped[int] = mapped_column(default=50)
    poaching: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    lifted_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SpeciesProtectionRow(Base):
    __tablename__ = "species_protections"
    __table_args__ = (Index("ix_species_protections_species", "species_entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    species_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    holder_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"), index=True)
    basis: Mapped[ProtectionBasis] = mapped_column(enum_type(ProtectionBasis, "basis"), default=ProtectionBasis.LAW)
    measures: Mapped[list[str]] = mapped_column(JSON, default=list)
    endangered_at_start: Mapped[bool] = mapped_column(default=False)
    since_epoch: Mapped[int] = mapped_column(default=0)
    recovered_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ConservationMovementRow(Base):
    __tablename__ = "conservation_movements"

    movement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    aims: Mapped[list[str]] = mapped_column(JSON, default=list)
    cohort_support: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
