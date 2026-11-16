from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import between, enum_type
from aerona.domain.enums.eras import TechFamily
from aerona.domain.models.genesis import TECH_LEVEL_CEILING

TECH_LEVEL_MAX = TECH_LEVEL_CEILING


class TechnologyProfileRow(Base):
    __tablename__ = "technology_profiles"
    __table_args__ = (between("level", 0, TECH_LEVEL_MAX),)

    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    family: Mapped[TechFamily] = mapped_column(enum_type(TechFamily, "family"), primary_key=True)
    level: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
