from enum import StrEnum

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base, CreatedAtMixin
from aerona.db.columns import enum_type


class MotifOverrideMode(StrEnum):
    PINNED = "pinned"
    ALLOWED = "allowed"


class MotifOverrideRow(CreatedAtMixin, Base):
    __tablename__ = "motif_overrides"
    __table_args__ = (UniqueConstraint("world_id", "motif", name="uq_motif_overrides_world_motif"), Index("ix_motif_overrides_world", "world_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    motif: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    mode: Mapped[MotifOverrideMode] = mapped_column(enum_type(MotifOverrideMode, "mode"))
