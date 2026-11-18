from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH, SHORT_TEXT_MAX_LENGTH
from aerona.db.base import Base, CreatedAtMixin, TimestampMixin
from aerona.db.columns import between, enum_type
from aerona.db.types import PydanticJSON, UtcDateTime
from aerona.domain.enums.epoch import DeferredStepKind, DeferredStepStatus, EngineStage, EpochPhase, EpochStepKind, EpochStepStatus
from aerona.domain.models.records import ChronicleAuditReport, EpochStatsData


class EpochRunRow(TimestampMixin, Base):
    __tablename__ = "epoch_runs"
    __table_args__ = (between("phase", EpochPhase.NOT_STARTED, EpochPhase.TRANSITION),)

    epoch: Mapped[int] = mapped_column(primary_key=True)
    phase: Mapped[int] = mapped_column(default=EpochPhase.NOT_STARTED)
    started: Mapped[bool] = mapped_column(default=False)
    finished: Mapped[bool] = mapped_column(default=False)
    engine_notes: Mapped[list[str]] = mapped_column(PydanticJSON(list[str]), default=list)
    resumed: Mapped[bool] = mapped_column(default=False)
    engine_since_chronicle_id: Mapped[int | None]
    started_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    finished_at: Mapped[datetime | None] = mapped_column(UtcDateTime())


class EpochStepRow(TimestampMixin, Base):
    __tablename__ = "epoch_steps"

    epoch: Mapped[int] = mapped_column(ForeignKey("epoch_runs.epoch", ondelete="CASCADE"), primary_key=True)
    step: Mapped[EpochStepKind] = mapped_column(enum_type(EpochStepKind, "step"), primary_key=True)
    status: Mapped[EpochStepStatus] = mapped_column(enum_type(EpochStepStatus, "status"), default=EpochStepStatus.PENDING)
    error: Mapped[str | None] = mapped_column(Text)


class EpochEnginePhaseRow(Base):
    __tablename__ = "epoch_engine_phases"

    epoch: Mapped[int] = mapped_column(ForeignKey("epoch_runs.epoch", ondelete="CASCADE"), primary_key=True)
    stage: Mapped[EngineStage] = mapped_column(enum_type(EngineStage, "stage"), primary_key=True)
    phase: Mapped[str] = mapped_column(String(SHORT_TEXT_MAX_LENGTH), primary_key=True)
    seconds: Mapped[float] = mapped_column(Float, default=0.0)


class EpochPhaseTimingRow(Base):
    __tablename__ = "epoch_phase_timings"
    __table_args__ = (between("phase", EpochPhase.GODS, EpochPhase.TRANSITION),)

    epoch: Mapped[int] = mapped_column(ForeignKey("epoch_runs.epoch", ondelete="CASCADE"), primary_key=True)
    phase: Mapped[int] = mapped_column(primary_key=True)
    started_offset_seconds: Mapped[float] = mapped_column(Float)
    duration_seconds: Mapped[float | None] = mapped_column(Float)


class DeferredStepRow(TimestampMixin, Base):
    __tablename__ = "deferred_steps"
    __table_args__ = (Index("ix_deferred_steps_status", "status", "epoch"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    epoch: Mapped[int]
    kind: Mapped[DeferredStepKind] = mapped_column(enum_type(DeferredStepKind, "kind"))
    status: Mapped[DeferredStepStatus] = mapped_column(enum_type(DeferredStepStatus, "status"), default=DeferredStepStatus.PENDING)
    requested_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result_world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="SET NULL"))
    attempts: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text)


class EpochRow(Base):
    __tablename__ = "epochs"
    __table_args__ = (CheckConstraint("year_end IS NULL OR year_start IS NULL OR year_end >= year_start", name="years_ordered"),)

    epoch: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(String(NAME_MAX_LENGTH))
    narrative: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    year_start: Mapped[int | None]
    year_end: Mapped[int | None]
    closed_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    chronicler_name: Mapped[str | None] = mapped_column(String(NAME_MAX_LENGTH))
    chronicler_identity: Mapped[str | None] = mapped_column(String(SHORT_TEXT_MAX_LENGTH))
    chronicler_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    audit: Mapped[ChronicleAuditReport | None] = mapped_column(PydanticJSON(ChronicleAuditReport))


class EpochWorldNarrativeRow(Base):
    __tablename__ = "epoch_world_narratives"

    epoch: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    narrative: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)


class EpochStatsRow(CreatedAtMixin, Base):
    __tablename__ = "epoch_stats"

    epoch: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[EpochStatsData] = mapped_column(PydanticJSON(EpochStatsData))
