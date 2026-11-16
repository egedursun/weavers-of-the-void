from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import between
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

REGION_TENSION_FIELDS = ("tension",)
SUBSYSTEM_TENSION_FIELDS = ("tension",)


class RegionalTensionRow(Base):
    __tablename__ = "regional_tensions"
    __table_args__ = (between("tension", PERCENT_MIN, PERCENT_MAX),)

    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), index=True)
    tension: Mapped[int] = mapped_column(default=0)
    crisis: Mapped[bool] = mapped_column(default=False)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SubsystemTensionRow(Base):
    __tablename__ = "subsystem_tensions"
    __table_args__ = (between("tension", PERCENT_MIN, PERCENT_MAX),)

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    subsystem: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH), primary_key=True)
    tension: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
