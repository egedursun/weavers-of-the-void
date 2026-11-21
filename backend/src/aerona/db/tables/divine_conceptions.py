from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import between, enum_type
from aerona.domain.enums.divine_conceptions import CreatorPlace, DivineCount, DivineNearness, DivinePersonhood, GodReading
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN


class DivineConceptionRow(Base):
    __tablename__ = "divine_conceptions"
    __table_args__ = (between("strain", PERCENT_MIN, PERCENT_MAX),)

    cult_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    count: Mapped[DivineCount] = mapped_column(enum_type(DivineCount, "count"), default=DivineCount.MANY)
    nearness: Mapped[DivineNearness] = mapped_column(enum_type(DivineNearness, "nearness"), default=DivineNearness.PRESENT)
    personhood: Mapped[DivinePersonhood] = mapped_column(enum_type(DivinePersonhood, "personhood"), default=DivinePersonhood.PERSONS)
    creator_place: Mapped[CreatorPlace] = mapped_column(enum_type(CreatorPlace, "creator_place"), default=CreatorPlace.UNKNOWN)
    strain: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class GodReadingRow(Base):
    __tablename__ = "god_readings"

    cult_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    reading: Mapped[GodReading] = mapped_column(enum_type(GodReading, "reading"), default=GodReading.UNKNOWN)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
