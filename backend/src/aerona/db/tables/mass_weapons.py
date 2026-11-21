from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.mass_weapons import MassHarm, MassReach, Posture, ProgrammeStage, RemnantKind


class MassWeaponRow(Base):
    __tablename__ = "mass_weapons"
    __table_args__ = (
        between("readiness", PERCENT_MIN, PERCENT_MAX),
        at_least("count", 0),
        at_least("begun_epoch", 0),
        Index("ix_mass_weapons_holder", "holder_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    harm: Mapped[MassHarm] = mapped_column(enum_type(MassHarm, "harm"), default=MassHarm.BLAST)
    reach: Mapped[MassReach] = mapped_column(enum_type(MassReach, "reach"), default=MassReach.SETTLEMENT)
    stage: Mapped[ProgrammeStage] = mapped_column(enum_type(ProgrammeStage, "stage"), default=ProgrammeStage.SOUGHT)
    count: Mapped[int] = mapped_column(default=0)
    readiness: Mapped[int] = mapped_column(default=0)
    seen_by: Mapped[list[int]] = mapped_column(JSON, default=list)
    begun_epoch: Mapped[int] = mapped_column(default=0)
    tested_epoch: Mapped[int | None]
    used_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DeterrencePostureRow(Base):
    __tablename__ = "deterrence_postures"
    __table_args__ = (
        between("credibility", PERCENT_MIN, PERCENT_MAX),
        Index("ix_deterrence_postures_holder", "holder_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    toward_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    posture: Mapped[Posture] = mapped_column(enum_type(Posture, "posture"), default=Posture.DECLARED)
    credibility: Mapped[int] = mapped_column(default=50)
    declared_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class WarRemnantRow(Base):
    __tablename__ = "war_remnants"
    __table_args__ = (
        between("density", PERCENT_MIN, PERCENT_MAX),
        between("cleared", PERCENT_MIN, PERCENT_MAX),
        at_least("decay_per_epoch", 0),
        Index("ix_war_remnants_region", "region_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    region_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    orbit_world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), index=True)
    kind: Mapped[RemnantKind] = mapped_column(enum_type(RemnantKind, "kind"), default=RemnantKind.BURIED_CHARGES)
    density: Mapped[int] = mapped_column(default=30)
    decay_per_epoch: Mapped[int] = mapped_column(default=3)
    war_id: Mapped[int | None] = mapped_column(ForeignKey("wars.id", ondelete="SET NULL"))
    weapon_id: Mapped[int | None] = mapped_column(ForeignKey("mass_weapons.id", ondelete="SET NULL"))
    cleared: Mapped[int] = mapped_column(default=0)
    created_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
