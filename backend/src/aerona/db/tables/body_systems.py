from sqlalchemy import JSON, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import between, enum_type
from aerona.domain.enums.body_systems import BodySystem, Sensitivity
from aerona.domain.enums.economy import CommodityKind


class BodySystemRow(Base):
    __tablename__ = "body_systems"
    __table_args__ = (
        UniqueConstraint("holder_entity_id", "system", name="uq_body_systems_holder_system"),
        between("air_need", 0, 100),
        between("gravity_max", 0, 100),
        between("cold_min", 0, 100),
        between("heat_max", 0, 100),
        between("diet_range", 0, 100),
        between("sleep_need", 0, 100),
        between("toxin_tolerance", 0, 100),
        between("radiation_max", 0, 100),
        between("light_min", 0, 100),
        between("humidity_range", 0, 100),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    system: Mapped[BodySystem] = mapped_column(enum_type(BodySystem, "system"))
    present: Mapped[bool] = mapped_column(default=True)
    air_need: Mapped[int] = mapped_column(default=25)
    gravity_max: Mapped[int] = mapped_column(default=75)
    cold_min: Mapped[int] = mapped_column(default=10)
    heat_max: Mapped[int] = mapped_column(default=80)
    diet_range: Mapped[int] = mapped_column(default=50)
    sleep_need: Mapped[int] = mapped_column(default=30)
    toxin_tolerance: Mapped[int] = mapped_column(default=40)
    radiation_max: Mapped[int] = mapped_column(default=40, server_default="40")
    light_min: Mapped[int] = mapped_column(default=0, server_default="0")
    humidity_range: Mapped[int] = mapped_column(default=100, server_default="100")
    strained: Mapped[bool] = mapped_column(default=False)
    failed: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SensitivityRow(Base):
    __tablename__ = "sensitivities"
    __table_args__ = (between("severity", 0, 100), Index("ix_sensitivities_holder", "holder_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[Sensitivity] = mapped_column(enum_type(Sensitivity, "kind"))
    trigger_commodity: Mapped[CommodityKind | None] = mapped_column(enum_type(CommodityKind, "trigger_commodity"))
    trigger_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    severity: Mapped[int] = mapped_column(default=30)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
