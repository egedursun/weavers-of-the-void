from sqlalchemy import JSON, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.integrity import Criticality, SectionHazard, SectionState
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.structure import SectionRole, StructureSection

STRUCTURE_SECTION_FIELDS = (
    "role",
    "criticality",
    "share",
    "exposure",
    "hazard",
    "neighbours",
    "condition",
    "state",
    "material",
    "world_material_id",
    "flammability",
)
DESIGN_SECTION_FIELDS = ("criticality", "share", "material")


class StructureSectionRow(Base):
    __tablename__ = "structure_sections"
    __table_args__ = (
        between("share", 0, PERCENT_MAX),
        between("exposure", 0, PERCENT_MAX),
        between("condition", PERCENT_MIN, PERCENT_MAX),
        between("flammability", PERCENT_MIN, PERCENT_MAX),
    )

    structure_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    section: Mapped[StructureSection] = mapped_column(enum_type(StructureSection, "section"), primary_key=True)
    role: Mapped[SectionRole] = mapped_column(enum_type(SectionRole, "role"))
    criticality: Mapped[Criticality] = mapped_column(enum_type(Criticality, "criticality"), default=Criticality.MINOR)
    share: Mapped[int] = mapped_column(default=10)
    exposure: Mapped[int] = mapped_column(default=10)
    hazard: Mapped[SectionHazard] = mapped_column(enum_type(SectionHazard, "hazard"), default=SectionHazard.NONE)
    neighbours: Mapped[list[str]] = mapped_column(JSON, default=list)
    condition: Mapped[int] = mapped_column(default=100)
    state: Mapped[SectionState] = mapped_column(enum_type(SectionState, "state"), default=SectionState.SOUND)
    material: Mapped[MaterialKind | None] = mapped_column(enum_type(MaterialKind, "material"))
    world_material_id: Mapped[int | None] = mapped_column(ForeignKey("world_materials.id", ondelete="SET NULL"))
    flammability: Mapped[int] = mapped_column(default=30)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class StructureDesignSectionRow(Base):
    __tablename__ = "structure_design_sections"
    __table_args__ = (between("share", 0, PERCENT_MAX),)

    design_id: Mapped[int] = mapped_column(ForeignKey("structure_designs.id", ondelete="CASCADE"), primary_key=True)
    section: Mapped[StructureSection] = mapped_column(enum_type(StructureSection, "section"), primary_key=True)
    criticality: Mapped[Criticality] = mapped_column(enum_type(Criticality, "criticality"), default=Criticality.MINOR)
    share: Mapped[int] = mapped_column(default=10)
    material: Mapped[MaterialKind | None] = mapped_column(enum_type(MaterialKind, "material"))


MEGASTRUCTURE_FIELDS = ("target_orbit", "output")


class MegastructureRow(Base):
    __tablename__ = "megastructure_states"
    __table_args__ = (at_least("output", 0), at_least("updated_epoch", 0))

    structure_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    target_orbit: Mapped[float | None] = mapped_column(Float)
    output: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
