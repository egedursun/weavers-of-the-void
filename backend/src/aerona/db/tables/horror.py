from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import enum_type
from aerona.domain.enums.horror import HorrorEffect, HorrorScope, HorrorSense, HorrorSource, HorrorTarget

HORROR_FIELDS = ("name", "target", "effect", "scope", "sense", "source", "duration", "sanity_cost", "leak", "until_epoch")


class HorrorEventRow(Base):
    __tablename__ = "horror_events"
    __table_args__ = (Index("ix_horror_events_world", "world_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    name: Mapped[str | None] = mapped_column(String(NAME_MAX_LENGTH))
    target: Mapped[HorrorTarget] = mapped_column(enum_type(HorrorTarget, "target"))
    effect: Mapped[HorrorEffect] = mapped_column(enum_type(HorrorEffect, "effect"))
    scope: Mapped[HorrorScope] = mapped_column(enum_type(HorrorScope, "scope"), default=HorrorScope.WORLD)
    sense: Mapped[HorrorSense] = mapped_column(enum_type(HorrorSense, "sense"), default=HorrorSense.SEEN)
    source: Mapped[HorrorSource] = mapped_column(enum_type(HorrorSource, "source"), default=HorrorSource.UNKNOWN)
    source_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    subject_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    duration: Mapped[int] = mapped_column(default=1)
    sanity_cost: Mapped[int] = mapped_column(default=5)
    leak: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)
    until_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
