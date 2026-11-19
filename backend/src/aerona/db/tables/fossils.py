from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.fossil import FossilReading, FossilSource, Preservation

FOSSIL_FIELDS = ("source", "richness", "frozen", "reading", "found_epoch", "layer", "preservation")


class FossilBedRow(Base):
    __tablename__ = "fossil_beds"
    __table_args__ = (between("richness", 1, 100), between("layer", 0, 100), at_least("laid_epoch", 0), Index("ix_fossil_beds_region", "region_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), index=True)
    source: Mapped[FossilSource] = mapped_column(enum_type(FossilSource, "source"))
    source_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), unique=True)
    richness: Mapped[int] = mapped_column(default=30)
    frozen: Mapped[bool] = mapped_column(default=False)
    disease_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    laid_epoch: Mapped[int] = mapped_column(default=0)
    found_epoch: Mapped[int | None]
    finder_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    reading: Mapped[FossilReading] = mapped_column(enum_type(FossilReading, "reading"), default=FossilReading.UNREAD)
    layer: Mapped[int] = mapped_column(default=0, server_default="0")
    preservation: Mapped[Preservation] = mapped_column(enum_type(Preservation, "preservation"), default=Preservation.ROCK, server_default="rock")
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
