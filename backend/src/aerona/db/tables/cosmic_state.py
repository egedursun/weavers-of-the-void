from sqlalchemy import Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.entity import CivilizationTier
from aerona.domain.enums.society import ResourceMechanic
from aerona.domain.enums.travel import VehicleKind


class VesselProfileRow(Base):
    __tablename__ = "vessel_profiles"

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[VehicleKind] = mapped_column(enum_type(VehicleKind, "kind"), index=True)


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
