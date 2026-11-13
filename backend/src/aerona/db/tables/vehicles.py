from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.collective import DesignComponentKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.integrity import Criticality, SectionHazard, SectionState
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.vehicles import MountArc, MountKind, VehicleSection, VehicleStatus

SECTION_FIELDS = ("function", "criticality", "share", "exposure", "armour", "hazard", "neighbours", "material_id", "size", "quality")
MOUNT_FIELDS = ("slot", "mount", "section", "model_id", "count", "arc")
GROUP_FIELDS = ("holder_node_id", "design_id", "count", "crewed", "condition", "fuel", "status", "region_entity_id")
GROUP_SECTION_FIELDS = ("damaged", "disabled", "destroyed")
VESSEL_SECTION_FIELDS = ("state", "condition")


class DesignSectionRow(Base):
    __tablename__ = "design_sections"
    __table_args__ = (
        between("share", 0, PERCENT_MAX),
        between("exposure", 0, PERCENT_MAX),
        between("armour", PERCENT_MIN, PERCENT_MAX),
        between("size", 0, 10),
        between("quality", PERCENT_MIN, PERCENT_MAX),
    )

    design_id: Mapped[int] = mapped_column(ForeignKey("designs.id", ondelete="CASCADE"), primary_key=True)
    section: Mapped[VehicleSection] = mapped_column(enum_type(VehicleSection, "section"), primary_key=True)
    function: Mapped[DesignComponentKind] = mapped_column(enum_type(DesignComponentKind, "function"))
    criticality: Mapped[Criticality] = mapped_column(enum_type(Criticality, "criticality"), default=Criticality.MINOR)
    share: Mapped[int] = mapped_column(default=10)
    exposure: Mapped[int] = mapped_column(default=10)
    armour: Mapped[int] = mapped_column(default=0)
    hazard: Mapped[SectionHazard] = mapped_column(enum_type(SectionHazard, "hazard"), default=SectionHazard.NONE)
    neighbours: Mapped[list[str]] = mapped_column(JSON, default=list)
    material_id: Mapped[int | None] = mapped_column(ForeignKey("world_materials.id", ondelete="SET NULL"))
    size: Mapped[int] = mapped_column(default=3)
    quality: Mapped[int] = mapped_column(default=50)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DesignMountRow(Base):
    __tablename__ = "design_mounts"
    __table_args__ = (at_least("slot", 0), at_least("count", 0), Index("ix_design_mounts_design", "design_id"), Index("ix_design_mounts_model", "model_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    design_id: Mapped[int] = mapped_column(ForeignKey("designs.id", ondelete="CASCADE"))
    slot: Mapped[int] = mapped_column(default=0)
    mount: Mapped[MountKind] = mapped_column(enum_type(MountKind, "mount"))
    section: Mapped[VehicleSection | None] = mapped_column(enum_type(VehicleSection, "section"))
    model_id: Mapped[int | None] = mapped_column(ForeignKey("equipment_models.id", ondelete="SET NULL"))
    count: Mapped[int] = mapped_column(default=1)
    arc: Mapped[MountArc] = mapped_column(enum_type(MountArc, "arc"), default=MountArc.ALL_ROUND)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DesignTechniqueRow(Base):
    __tablename__ = "design_techniques"

    design_id: Mapped[int] = mapped_column(ForeignKey("designs.id", ondelete="CASCADE"), primary_key=True)
    technique: Mapped[Technique] = mapped_column(enum_type(Technique, "technique"), primary_key=True)


class VehicleGroupRow(Base):
    __tablename__ = "vehicle_groups"
    __table_args__ = (
        at_least("count", 0),
        at_least("crewed", 0),
        between("condition", PERCENT_MIN, PERCENT_MAX),
        at_least("fuel", 0),
        at_least("built_epoch", 0),
        Index("ix_vehicle_groups_holder", "holder_node_id"),
        Index("ix_vehicle_groups_design", "design_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    design_id: Mapped[int] = mapped_column(ForeignKey("designs.id", ondelete="CASCADE"))
    count: Mapped[int] = mapped_column(default=1)
    crewed: Mapped[int] = mapped_column(default=0)
    condition: Mapped[int] = mapped_column(default=100)
    fuel: Mapped[int] = mapped_column(default=0)
    status: Mapped[VehicleStatus] = mapped_column(enum_type(VehicleStatus, "status"), default=VehicleStatus.READY)
    region_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    built_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class VehicleGroupSectionRow(Base):
    __tablename__ = "vehicle_group_sections"
    __table_args__ = (at_least("damaged", 0), at_least("disabled", 0), at_least("destroyed", 0))

    group_id: Mapped[int] = mapped_column(ForeignKey("vehicle_groups.id", ondelete="CASCADE"), primary_key=True)
    section: Mapped[VehicleSection] = mapped_column(enum_type(VehicleSection, "section"), primary_key=True)
    damaged: Mapped[int] = mapped_column(default=0)
    disabled: Mapped[int] = mapped_column(default=0)
    destroyed: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class VesselSectionRow(Base):
    __tablename__ = "vessel_sections"
    __table_args__ = (between("condition", PERCENT_MIN, PERCENT_MAX),)

    vessel_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    section: Mapped[VehicleSection] = mapped_column(enum_type(VehicleSection, "section"), primary_key=True)
    state: Mapped[SectionState] = mapped_column(enum_type(SectionState, "state"), default=SectionState.SOUND)
    condition: Mapped[int] = mapped_column(default=100)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
