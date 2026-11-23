from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.museum import HoardKind, PieceKind

HOARD_FIELDS = ("kind", "prestige")
PIECE_FIELDS = ("kind", "polity_entity_id")


class MuseumCollectionRow(Base):
    __tablename__ = "museum_collections"
    __table_args__ = (between("prestige", 0, 100), at_least("founded_epoch", 0), Index("ix_museum_collections_keeper", "keeper_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    keeper_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    structure_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    kind: Mapped[HoardKind] = mapped_column(enum_type(HoardKind, "kind"))
    prestige: Mapped[int] = mapped_column(default=0)
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MuseumPieceRow(Base):
    __tablename__ = "museum_pieces"
    __table_args__ = (at_least("acquired_epoch", 0), Index("ix_museum_pieces_collection", "collection_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("museum_collections.id", ondelete="CASCADE"))
    kind: Mapped[PieceKind] = mapped_column(enum_type(PieceKind, "kind"))
    item_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), unique=True)
    fossil_bed_id: Mapped[int | None] = mapped_column(ForeignKey("fossil_beds.id", ondelete="SET NULL"), unique=True)
    acquired_epoch: Mapped[int] = mapped_column(default=0)
    looted_from_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    polity_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    returned_epoch: Mapped[int | None]
    returned_by_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
