from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.fortune import FortuneLaw, FortuneSourceKind


class FortuneProfileRow(Base):
    __tablename__ = "fortune_profiles"
    __table_args__ = (between("fortune", -100, 100), between("streak", -100, 100))

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    fortune: Mapped[int] = mapped_column(default=0)
    streak: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class FortuneSourceRow(Base):
    __tablename__ = "fortune_sources"
    __table_args__ = (between("strength", -100, 100), Index("ix_fortune_sources_holder", "holder_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[FortuneSourceKind] = mapped_column(enum_type(FortuneSourceKind, "kind"))
    strength: Mapped[int] = mapped_column(default=10)
    giver_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    until_epoch: Mapped[int | None]
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CohortMishapRateRow(Base):
    __tablename__ = "cohort_mishap_rates"
    __table_args__ = (at_least("injured", 0), at_least("dead", 0))

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    epoch: Mapped[int] = mapped_column(primary_key=True)
    injured: Mapped[int] = mapped_column(default=0)
    dead: Mapped[int] = mapped_column(default=0)
    rate_pct: Mapped[int] = mapped_column(default=0)
    by_exposure: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)


class FortuneLawRow(Base):
    __tablename__ = "fortune_laws"

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    law: Mapped[FortuneLaw] = mapped_column(enum_type(FortuneLaw, "law"), default=FortuneLaw.PERSONAL)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
