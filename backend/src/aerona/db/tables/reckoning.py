from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.polity import GovernmentKind
from aerona.domain.enums.reckoning import CaseOutcome, MeasureStage, ReckoningMeasure


class ReckoningRow(Base):
    __tablename__ = "reckonings"
    __table_args__ = (
        between("resistance", PERCENT_MIN, PERCENT_MAX),
        between("victims_pressure", PERCENT_MIN, PERCENT_MAX),
        at_least("opened_epoch", 0),
        at_least("fallen_epoch", 0),
        Index("ix_reckonings_polity", "polity_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    fallen_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    fallen_government: Mapped[GovernmentKind | None] = mapped_column(enum_type(GovernmentKind, "fallen_government"))
    fallen_epoch: Mapped[int] = mapped_column(default=0)
    opened_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    resistance: Mapped[int] = mapped_column(default=30)
    victims_pressure: Mapped[int] = mapped_column(default=30)
    opened_epoch: Mapped[int] = mapped_column(default=0)
    closed_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ReckoningMeasureRow(Base):
    __tablename__ = "reckoning_measures"
    __table_args__ = (
        between("scope", PERCENT_MIN, PERCENT_MAX),
        between("strength", PERCENT_MIN, PERCENT_MAX),
        at_least("admin_taken", 0),
        at_least("started_epoch", 0),
        Index("ix_reckoning_measures_reckoning", "reckoning_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reckoning_id: Mapped[int] = mapped_column(ForeignKey("reckonings.id", ondelete="CASCADE"))
    polity_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    measure: Mapped[ReckoningMeasure] = mapped_column(enum_type(ReckoningMeasure, "measure"), default=ReckoningMeasure.TRIBUNAL)
    scope: Mapped[int] = mapped_column(default=50)
    strength: Mapped[int] = mapped_column(default=50)
    stage: Mapped[MeasureStage] = mapped_column(enum_type(MeasureStage, "stage"), default=MeasureStage.PLANNED)
    admin_taken: Mapped[int] = mapped_column(default=0)
    started_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ReckoningCaseRow(Base):
    __tablename__ = "reckoning_cases"
    __table_args__ = (
        at_least("epoch", 0),
        Index("ix_reckoning_cases_reckoning", "reckoning_id"),
        Index("ix_reckoning_cases_accused", "accused_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reckoning_id: Mapped[int] = mapped_column(ForeignKey("reckonings.id", ondelete="CASCADE"))
    accused_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    incident_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    measure: Mapped[ReckoningMeasure] = mapped_column(enum_type(ReckoningMeasure, "measure"), default=ReckoningMeasure.TRIBUNAL)
    outcome: Mapped[CaseOutcome] = mapped_column(enum_type(CaseOutcome, "outcome"), default=CaseOutcome.PENDING)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
