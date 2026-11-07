from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.statecraft import CrisisDemand, CrisisSide, CrisisState


class PolityRegardRow(Base):
    __tablename__ = "polity_regard"
    __table_args__ = (
        between("threat", PERCENT_MIN, PERCENT_MAX),
        between("trust", PERCENT_MIN, PERCENT_MAX),
        Index("ix_polity_regard_subject", "subject_entity_id"),
    )

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    subject_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    threat: Mapped[int] = mapped_column(default=0)
    trust: Mapped[int] = mapped_column(default=50)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DiplomacyProfileRow(Base):
    __tablename__ = "diplomacy_profiles"
    __table_args__ = (at_least("capacity", 0), at_least("relations", 0), at_least("strain", 0))

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    capacity: Mapped[int] = mapped_column(default=2)
    relations: Mapped[int] = mapped_column(default=0)
    strain: Mapped[int] = mapped_column(default=0)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CrisisRow(Base):
    __tablename__ = "crises"
    __table_args__ = (at_least("escalation", 0), at_least("amount", 0), at_least("opened_epoch", 0), Index("ix_crises_demander", "demander_entity_id", "state"))

    id: Mapped[int] = mapped_column(primary_key=True)
    demander_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    target_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    demand: Mapped[CrisisDemand] = mapped_column(enum_type(CrisisDemand, "demand"))
    subject_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    amount: Mapped[int] = mapped_column(default=0)
    escalation: Mapped[int] = mapped_column(default=0)
    state: Mapped[CrisisState] = mapped_column(enum_type(CrisisState, "state"), default=CrisisState.ESCALATING)
    opened_epoch: Mapped[int] = mapped_column(default=0)
    resolved_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CrisisBackerRow(Base):
    __tablename__ = "crisis_backers"
    __table_args__ = (between("promised", PERCENT_MIN, PERCENT_MAX),)

    crisis_id: Mapped[int] = mapped_column(ForeignKey("crises.id", ondelete="CASCADE"), primary_key=True)
    backer_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True, index=True)
    side: Mapped[CrisisSide] = mapped_column(enum_type(CrisisSide, "side"))
    promised: Mapped[int] = mapped_column(default=0)
    swing: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[bool] = mapped_column(default=False)


class SphereRow(Base):
    __tablename__ = "spheres"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX), at_least("since_epoch", 0))

    power_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    client_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True, index=True)
    strength: Mapped[int] = mapped_column(default=30)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[bool] = mapped_column(default=False)
