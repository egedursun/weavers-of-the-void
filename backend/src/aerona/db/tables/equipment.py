from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.body import DamageType
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.equipment import ArmamentSlot, EquipmentFamily
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.powers import PowerDeviceEffect

MODEL_FIELDS = (
    "name",
    "description",
    "world_id",
    "origin_node_id",
    "slot",
    "family",
    "material",
    "world_material_id",
    "quality",
    "technique",
    "tech_level",
    "power_effect",
    "damage",
    "piercing",
    "reach",
    "rate",
    "accuracy",
    "damage_type",
    "ammunition",
    "crew",
    "protection",
    "coverage",
    "weight",
    "cost",
    "renown",
    "retired",
)


class EquipmentModelRow(Base):
    __tablename__ = "equipment_models"
    __table_args__ = (
        between("quality", PERCENT_MIN, PERCENT_MAX),
        between("tech_level", 0, 10),
        between("damage", PERCENT_MIN, PERCENT_MAX),
        between("piercing", PERCENT_MIN, PERCENT_MAX),
        at_least("reach", 0),
        at_least("rate", 0),
        between("accuracy", PERCENT_MIN, PERCENT_MAX),
        at_least("crew", 0),
        between("protection", PERCENT_MIN, PERCENT_MAX),
        between("coverage", PERCENT_MIN, PERCENT_MAX),
        at_least("weight", 0),
        at_least("cost", 0),
        between("renown", PERCENT_MIN, PERCENT_MAX),
        at_least("created_epoch", 0),
        Index("ix_equipment_models_world", "world_id"),
        Index("ix_equipment_models_origin", "origin_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), unique=True)
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    description: Mapped[str | None] = mapped_column(Text)
    origin_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    slot: Mapped[ArmamentSlot] = mapped_column(enum_type(ArmamentSlot, "slot"))
    family: Mapped[EquipmentFamily] = mapped_column(enum_type(EquipmentFamily, "family"))
    material: Mapped[MaterialKind | None] = mapped_column(enum_type(MaterialKind, "material"))
    world_material_id: Mapped[int | None] = mapped_column(ForeignKey("world_materials.id", ondelete="SET NULL"))
    quality: Mapped[int] = mapped_column(default=50)
    technique: Mapped[Technique | None] = mapped_column(enum_type(Technique, "technique"))
    tech_level: Mapped[int] = mapped_column(default=0)
    damage: Mapped[int] = mapped_column(default=0)
    piercing: Mapped[int] = mapped_column(default=0)
    reach: Mapped[int] = mapped_column(default=0)
    rate: Mapped[int] = mapped_column(default=1)
    accuracy: Mapped[int] = mapped_column(default=0)
    damage_type: Mapped[DamageType] = mapped_column(enum_type(DamageType, "damage_type"), default=DamageType.BLUNT)
    ammunition: Mapped[CommodityKind | None] = mapped_column(enum_type(CommodityKind, "ammunition"))
    crew: Mapped[int] = mapped_column(default=0)
    protection: Mapped[int] = mapped_column(default=0)
    coverage: Mapped[int] = mapped_column(default=0)
    weight: Mapped[int] = mapped_column(default=0)
    cost: Mapped[int] = mapped_column(default=1)
    renown: Mapped[int] = mapped_column(default=0)
    parent_model_id: Mapped[int | None] = mapped_column(ForeignKey("equipment_models.id", ondelete="SET NULL"))
    created_epoch: Mapped[int] = mapped_column(default=0)
    retired: Mapped[bool] = mapped_column(default=False)
    power_effect: Mapped[PowerDeviceEffect | None] = mapped_column(enum_type(PowerDeviceEffect, "power_effect"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class EquipmentStoreRow(Base):
    __tablename__ = "equipment_stores"
    __table_args__ = (at_least("count", 0), Index("ix_equipment_stores_model", "model_id"))

    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("equipment_models.id", ondelete="CASCADE"), primary_key=True)
    count: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ArmyUnitEquipmentRow(Base):
    __tablename__ = "army_unit_equipment"
    __table_args__ = (at_least("count", 0), between("condition", PERCENT_MIN, PERCENT_MAX), Index("ix_army_unit_equipment_model", "model_id"))

    unit_id: Mapped[int] = mapped_column(ForeignKey("army_units.id", ondelete="CASCADE"), primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("equipment_models.id", ondelete="CASCADE"), primary_key=True)
    count: Mapped[int] = mapped_column(default=0)
    condition: Mapped[int] = mapped_column(default=100)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class UnitDesignEquipmentRow(Base):
    __tablename__ = "unit_design_equipment"
    __table_args__ = (between("count", 1, 10), Index("ix_unit_design_equipment_model", "model_id"))

    design_id: Mapped[int] = mapped_column(ForeignKey("unit_designs.id", ondelete="CASCADE"), primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("equipment_models.id", ondelete="CASCADE"), primary_key=True)
    count: Mapped[int] = mapped_column(default=1)


class UnitDesignTechniqueRow(Base):
    __tablename__ = "unit_design_techniques"

    design_id: Mapped[int] = mapped_column(ForeignKey("unit_designs.id", ondelete="CASCADE"), primary_key=True)
    technique: Mapped[Technique] = mapped_column(enum_type(Technique, "technique"), primary_key=True)
