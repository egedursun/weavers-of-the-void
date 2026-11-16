from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import enum_type
from aerona.domain.enums.divine import CouncilSeat, EscalationStep, VotingRule

PROCEDURE_FIELDS = ("quorum_pct", "voting_rule", "creator_veto", "term_epochs")
SEAT_FIELDS = ("seat", "excluded_until")
VIOLATION_FIELDS = ("step",)


class CouncilProcedureRow(Base):
    __tablename__ = "council_procedures"

    id: Mapped[int] = mapped_column(primary_key=True)
    quorum_pct: Mapped[int] = mapped_column(default=50)
    voting_rule: Mapped[VotingRule] = mapped_column(enum_type(VotingRule, "voting_rule"), default=VotingRule.MAJORITY)
    creator_veto: Mapped[bool] = mapped_column(default=True)
    term_epochs: Mapped[int] = mapped_column(default=10)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DivineSeatRow(Base):
    __tablename__ = "divine_council_seats"

    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    seat: Mapped[CouncilSeat] = mapped_column(enum_type(CouncilSeat, "seat"), default=CouncilSeat.BY_RIGHT)
    since_epoch: Mapped[int] = mapped_column(default=0)
    excluded_until: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CouncilViolationRow(Base):
    __tablename__ = "council_violations"
    __table_args__ = (Index("ix_council_violations_violator", "violator_node_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ruling_id: Mapped[int | None] = mapped_column(ForeignKey("council_rulings.id", ondelete="SET NULL"))
    violator_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    epoch: Mapped[int] = mapped_column(default=0)
    step: Mapped[EscalationStep] = mapped_column(enum_type(EscalationStep, "step"), default=EscalationStep.CENSURE)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
