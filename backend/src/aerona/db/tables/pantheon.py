from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import enum_type
from aerona.domain.enums.foreign_god import PantheonStructure, PantheonTie

PANTHEON_FIELDS = ("structure", "head_node_id")
TIE_FIELDS = ("tie",)
SYNCRETISM_FIELDS = ("dominant_node_id",)


class PantheonStructureRow(Base):
    __tablename__ = "pantheon_structures"

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    structure: Mapped[PantheonStructure] = mapped_column(enum_type(PantheonStructure, "structure"), default=PantheonStructure.LOOSE)
    head_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PantheonTieRow(Base):
    __tablename__ = "pantheon_ties"
    __table_args__ = (CheckConstraint("god_node_id <> other_node_id", name="two_gods"), Index("ix_pantheon_ties_other", "other_node_id"))

    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    other_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    tie: Mapped[PantheonTie] = mapped_column(enum_type(PantheonTie, "tie"), default=PantheonTie.KIN)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SyncretismRow(Base):
    __tablename__ = "syncretisms"
    __table_args__ = (Index("ix_syncretisms_people", "people_entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    foreign_god_id: Mapped[int] = mapped_column(ForeignKey("foreign_gods.id", ondelete="CASCADE"))
    son_id: Mapped[int] = mapped_column(ForeignKey("sons.id", ondelete="CASCADE"))
    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    dominant_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
