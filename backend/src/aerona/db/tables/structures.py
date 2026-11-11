from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.demography import Aesthetic
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.structure import STRUCTURE_LEVEL_MAX, BuilderKind, BuildScale, ConstructionState, ConstructionStatus, StaffScale, StructureKind


class StructureDesignRow(Base):
    __tablename__ = "structure_designs"
    __table_args__ = (
        between("capacity_pct", 0, 1000),
        between("cost_pct", 1, 1000),
        between("upkeep_pct", 0, 1000),
        between("function_pct", 0, 300),
        between("staff_pct", 0, 1000),
        Index("ix_structure_designs_world", "world_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    description: Mapped[str | None] = mapped_column(Text)
    base_kind: Mapped[StructureKind] = mapped_column(enum_type(StructureKind, "base_kind"))
    staff_class: Mapped[SocialClass | None] = mapped_column(enum_type(SocialClass, "staff_class"))
    staff_scale: Mapped[StaffScale | None] = mapped_column(enum_type(StaffScale, "staff_scale"))
    scale: Mapped[BuildScale | None] = mapped_column(enum_type(BuildScale, "scale"))
    upkeep_commodity: Mapped[CommodityKind | None] = mapped_column(enum_type(CommodityKind, "upkeep_commodity"))
    min_tier: Mapped[SizeTier | None] = mapped_column(enum_type(SizeTier, "min_tier"))
    ley: Mapped[bool | None]
    capacity_pct: Mapped[int] = mapped_column(default=100)
    cost_pct: Mapped[int] = mapped_column(default=100)
    upkeep_pct: Mapped[int] = mapped_column(default=100)
    function_pct: Mapped[int] = mapped_column(default=100)
    staff_pct: Mapped[int] = mapped_column(default=100)
    creator_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    created_epoch: Mapped[int] = mapped_column(default=0)
    retired: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class StructureProfileRow(Base):
    __tablename__ = "structure_profiles"
    __table_args__ = (
        between("level", 1, STRUCTURE_LEVEL_MAX),
        between("condition", PERCENT_MIN, PERCENT_MAX),
        between("progress", PERCENT_MIN, PERCENT_MAX),
        between("fire_resistance", PERCENT_MIN, PERCENT_MAX),
        between("effect_pct", PERCENT_MIN, PERCENT_MAX),
        between("staff_pct", PERCENT_MIN, PERCENT_MAX),
        at_least("capacity", 0),
        at_least("upkeep_coin", 0),
        at_least("upkeep_goods", 0),
        at_least("unpaid_epochs", 0),
        Index("ix_structure_profiles_host", "host_entity_id"),
        Index("ix_structure_profiles_kind", "kind"),
    )

    structure_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[StructureKind] = mapped_column(enum_type(StructureKind, "structure_kind"))
    design_id: Mapped[int | None] = mapped_column(ForeignKey("structure_designs.id", ondelete="SET NULL"))
    level: Mapped[int] = mapped_column(default=1)
    capacity: Mapped[int] = mapped_column(default=0)
    condition: Mapped[int] = mapped_column(default=100)
    construction_state: Mapped[ConstructionState] = mapped_column(enum_type(ConstructionState, "construction_state"), default=ConstructionState.COMPLETE)
    progress: Mapped[int] = mapped_column(default=100)
    fire_resistance: Mapped[int] = mapped_column(default=50)
    host_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    district_id: Mapped[int | None] = mapped_column(ForeignKey("districts.id", ondelete="SET NULL"))
    builder_entity_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    builder_kind: Mapped[BuilderKind | None] = mapped_column(enum_type(BuilderKind, "builder_kind"))
    architect_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    dedicated_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    aesthetic: Mapped[Aesthetic | None] = mapped_column(enum_type(Aesthetic, "aesthetic"))
    on_ley_line: Mapped[bool] = mapped_column(default=False)
    anchor: Mapped[bool] = mapped_column(default=False)
    effect_pct: Mapped[int] = mapped_column(default=0)
    staff_pct: Mapped[int] = mapped_column(default=0)
    upkeep_coin: Mapped[int] = mapped_column(default=0)
    upkeep_goods: Mapped[int] = mapped_column(default=0)
    unpaid_epochs: Mapped[int] = mapped_column(default=0)
    built_epoch: Mapped[int | None]
    obsolete_since: Mapped[int | None]
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class StructureStaffRow(Base):
    __tablename__ = "structure_staff"
    __table_args__ = (at_least("required", 0), at_least("allocated", 0), Index("ix_structure_staff_community", "community_entity_id"))

    structure_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    social_class: Mapped[SocialClass] = mapped_column(enum_type(SocialClass, "social_class"), primary_key=True)
    community_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    required: Mapped[int] = mapped_column(default=0)
    allocated: Mapped[int] = mapped_column(default=0)
    held: Mapped[bool] = mapped_column(default=False)


class ConstructionRow(Base):
    __tablename__ = "constructions"
    __table_args__ = (
        at_least("cost", 1),
        at_least("progress", 0),
        at_least("funds", 0),
        at_least("workers", 0),
        between("materials_pct", PERCENT_MIN, PERCENT_MAX),
        at_least("stalled_epochs", 0),
        at_least("generations", 0),
        Index("ix_constructions_structure", "structure_entity_id"),
        Index("ix_constructions_site", "site_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    structure_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    site_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    builder_entity_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    kind: Mapped[StructureKind] = mapped_column(enum_type(StructureKind, "structure_kind"))
    design_id: Mapped[int | None] = mapped_column(ForeignKey("structure_designs.id", ondelete="SET NULL"))
    status: Mapped[ConstructionStatus] = mapped_column(enum_type(ConstructionStatus, "status"), default=ConstructionStatus.ACTIVE)
    cost: Mapped[int] = mapped_column(default=1)
    progress: Mapped[int] = mapped_column(default=0)
    funds: Mapped[int] = mapped_column(default=0)
    workers: Mapped[int] = mapped_column(default=0)
    materials_pct: Mapped[int] = mapped_column(default=0)
    stalled_epochs: Mapped[int] = mapped_column(default=0)
    generations: Mapped[int] = mapped_column(default=0)
    player: Mapped[bool] = mapped_column(default=False)
    started_epoch: Mapped[int]
    finished_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
