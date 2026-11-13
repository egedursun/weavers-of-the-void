from sqlalchemy import JSON, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.entity import CivilizationTier
from aerona.domain.enums.military import VesselStatus
from aerona.domain.enums.society import ResourceMechanic
from aerona.domain.enums.travel import VehicleKind
from aerona.domain.enums.vehicles import VehicleFrame


class VesselProfileRow(Base):
    __tablename__ = "vessel_profiles"
    __table_args__ = (
        between("condition", 0, 100),
        between("seaworthiness", 0, 100),
        between("seamanship", 0, 100),
        at_least("cargo_capacity", 0),
        at_least("crew", 0),
        at_least("renown", 0),
    )

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[VehicleKind] = mapped_column(enum_type(VehicleKind, "kind"), index=True)
    frame: Mapped[VehicleFrame] = mapped_column(enum_type(VehicleFrame, "frame"), default=VehicleFrame.BOAT)
    hull_material: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    fabric_material: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    condition: Mapped[int] = mapped_column(default=100)
    armament: Mapped[list[str]] = mapped_column(JSON, default=list)
    seaworthiness: Mapped[int] = mapped_column(default=50)
    cargo_capacity: Mapped[int] = mapped_column(default=0)
    crew: Mapped[int] = mapped_column(default=0)
    seamanship: Mapped[int] = mapped_column(default=0)
    captain_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    home_port_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    crew_community_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    region_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    fleet_army_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    legend_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    renown: Mapped[int] = mapped_column(default=0)
    status: Mapped[VesselStatus] = mapped_column(enum_type(VesselStatus, "status"), default=VesselStatus.DOCKED)
    voyages: Mapped[int] = mapped_column(default=0)
    design_id: Mapped[int | None] = mapped_column(ForeignKey("designs.id", ondelete="SET NULL"))
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ResourceMechanicRow(Base):
    __tablename__ = "resource_mechanics"

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    mechanic: Mapped[ResourceMechanic] = mapped_column(enum_type(ResourceMechanic, "mechanic"), primary_key=True, index=True)
    magnitude: Mapped[int | None]
    epochs: Mapped[int | None]


class AddictionImmunityRow(Base):
    __tablename__ = "addiction_immunities"
    __table_args__ = (at_least("recovered_epoch", 0),)

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    resource_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    recovered_epoch: Mapped[int]


class WorldLeakItemRow(Base):
    __tablename__ = "world_leak_items"
    __table_args__ = (Index("ix_world_leak_items_epoch_world", "epoch", "world_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    epoch: Mapped[int]
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    item: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    delta: Mapped[float] = mapped_column(Float)


class CivilizationTierLockRow(Base):
    __tablename__ = "civilization_tier_locks"
    __table_args__ = (between("tier", CivilizationTier.TRIBE, max(CivilizationTier)),)

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    tier: Mapped[int]
    since_epoch: Mapped[int]
