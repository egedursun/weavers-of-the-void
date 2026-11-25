from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, LargeBinary, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.authorship import OwnedByAccount
from aerona.db.base import Base
from aerona.db.columns import at_least, enum_type
from aerona.domain.enums.divine_will import (
    ArtifactFormat,
    ArtifactKind,
    ArtifactStatus,
    AttachmentKind,
    AttachmentStatus,
    ChunkSource,
    ConfirmationReason,
    ConfirmationStatus,
    CycleEventKind,
    CycleStatus,
    DivineWillMode,
    ForecastStatus,
    PlanStatus,
    StepImpact,
    StepStatus,
)


def created() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class DivineWillSessionRow(OwnedByAccount, Base):
    __tablename__ = "divine_will_sessions"
    __table_args__ = (at_least("opened_epoch", 0),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(default="")
    opened_epoch: Mapped[int]
    opened_at: Mapped[datetime] = created()
    closed_epoch: Mapped[int | None]
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DivineWillCycleRow(Base):
    __tablename__ = "divine_will_cycles"
    __table_args__ = (
        UniqueConstraint("session_id", "ordinal", name="uq_divine_will_cycles_ordinal"),
        at_least("ordinal", 1),
        at_least("epoch", 0),
        at_least("input_tokens", 0),
        at_least("output_tokens", 0),
        at_least("steps", 0),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("divine_will_sessions.id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int]
    mode: Mapped[DivineWillMode] = mapped_column(enum_type(DivineWillMode, "mode"))
    epoch: Mapped[int]
    status: Mapped[CycleStatus] = mapped_column(enum_type(CycleStatus, "status"), default=CycleStatus.RUNNING)
    player_text: Mapped[str] = mapped_column(Text)
    final_text: Mapped[str] = mapped_column(Text, default="")
    model: Mapped[str] = mapped_column(default="")
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    steps: Mapped[int] = mapped_column(default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = created()
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DivineWillEventRow(Base):
    __tablename__ = "divine_will_events"
    __table_args__ = (UniqueConstraint("cycle_id", "ordinal", name="uq_divine_will_events_ordinal"), at_least("ordinal", 1))

    id: Mapped[int] = mapped_column(primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("divine_will_cycles.id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int]
    kind: Mapped[CycleEventKind] = mapped_column(enum_type(CycleEventKind, "kind"))
    tool: Mapped[str] = mapped_column(default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    handle: Mapped[str] = mapped_column(default="")
    created_at: Mapped[datetime] = created()


class DivineWillHandleRow(Base):
    __tablename__ = "divine_will_handles"
    __table_args__ = (at_least("total", 0),)

    key: Mapped[str] = mapped_column(primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("divine_will_cycles.id", ondelete="CASCADE"), index=True)
    tool: Mapped[str]
    query: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    total: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = created()


class DivineWillConfirmationRow(Base):
    __tablename__ = "divine_will_confirmations"

    id: Mapped[int] = mapped_column(primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("divine_will_cycles.id", ondelete="CASCADE"), index=True)
    action_id: Mapped[str]
    input: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    reason: Mapped[ConfirmationReason] = mapped_column(enum_type(ConfirmationReason, "reason"))
    preview: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[ConfirmationStatus] = mapped_column(enum_type(ConfirmationStatus, "status"), default=ConfirmationStatus.PENDING)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ledger_entry_id: Mapped[int | None] = mapped_column(ForeignKey("ledger_entries.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = created()


class DivineWillAttachmentRow(Base):
    __tablename__ = "divine_will_attachments"
    __table_args__ = (at_least("size", 0),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cycle_id: Mapped[int | None] = mapped_column(ForeignKey("divine_will_cycles.id", ondelete="CASCADE"), index=True)
    kind: Mapped[AttachmentKind] = mapped_column(enum_type(AttachmentKind, "kind"))
    filename: Mapped[str]
    mime: Mapped[str]
    size: Mapped[int]
    media_key: Mapped[str]
    markdown_key: Mapped[str] = mapped_column(default="")
    status: Mapped[AttachmentStatus] = mapped_column(enum_type(AttachmentStatus, "status"), default=AttachmentStatus.STORED)
    seen_by_model: Mapped[bool] = mapped_column(default=False)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = created()


class DivineWillChunkRow(Base):
    __tablename__ = "divine_will_chunks"
    __table_args__ = (
        Index("ix_divine_will_chunks_source", "source", "source_id"),
        at_least("ordinal", 0),
        at_least("tokens", 0),
        at_least("updated_epoch", 0),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[ChunkSource] = mapped_column(enum_type(ChunkSource, "source"))
    source_id: Mapped[str]
    node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    cycle_id: Mapped[int | None] = mapped_column(ForeignKey("divine_will_cycles.id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int] = mapped_column(default=0)
    text: Mapped[str] = mapped_column(Text)
    tokens: Mapped[int] = mapped_column(default=0)
    vector: Mapped[bytes] = mapped_column(LargeBinary)
    digest: Mapped[str]
    updated_epoch: Mapped[int] = mapped_column(default=0)


class DivineWillArtifactRow(OwnedByAccount, Base):
    __tablename__ = "divine_will_artifacts"
    __table_args__ = (at_least("current_version", 1),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    kind: Mapped[ArtifactKind] = mapped_column(enum_type(ArtifactKind, "kind"))
    format: Mapped[ArtifactFormat] = mapped_column(enum_type(ArtifactFormat, "format"))
    status: Mapped[ArtifactStatus] = mapped_column(enum_type(ArtifactStatus, "status"), default=ArtifactStatus.DRAFT)
    language: Mapped[str] = mapped_column(default="")
    mode: Mapped[DivineWillMode] = mapped_column(enum_type(DivineWillMode, "mode"))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_cycle_id: Mapped[int | None] = mapped_column(ForeignKey("divine_will_cycles.id", ondelete="SET NULL"))
    current_version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = created()


class DivineWillArtifactVersionRow(Base):
    __tablename__ = "divine_will_artifact_versions"
    __table_args__ = (at_least("version", 1),)

    artifact_id: Mapped[int] = mapped_column(ForeignKey("divine_will_artifacts.id", ondelete="CASCADE"), primary_key=True)
    version: Mapped[int] = mapped_column(primary_key=True)
    body: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="")
    cycle_id: Mapped[int | None] = mapped_column(ForeignKey("divine_will_cycles.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = created()


class DivineWillArtifactNodeRow(Base):
    __tablename__ = "divine_will_artifact_nodes"

    artifact_id: Mapped[int] = mapped_column(ForeignKey("divine_will_artifacts.id", ondelete="CASCADE"), primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True, index=True)


class DivineWillPlanRow(OwnedByAccount, Base):
    __tablename__ = "divine_will_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    cycle_id: Mapped[int | None] = mapped_column(ForeignKey("divine_will_cycles.id", ondelete="SET NULL"), index=True)
    artifact_id: Mapped[int | None] = mapped_column(ForeignKey("divine_will_artifacts.id", ondelete="SET NULL"))
    title: Mapped[str]
    status: Mapped[PlanStatus] = mapped_column(enum_type(PlanStatus, "status"), default=PlanStatus.DRAFT)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created()


class DivineWillPlanStepRow(Base):
    __tablename__ = "divine_will_plan_steps"
    __table_args__ = (at_least("ordinal", 1), at_least("estimated_essence", 0))

    plan_id: Mapped[int] = mapped_column(ForeignKey("divine_will_plans.id", ondelete="CASCADE"), primary_key=True)
    ordinal: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    action_id: Mapped[str]
    input: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    depends_on: Mapped[list[int]] = mapped_column(JSON, default=list)
    declared_impact: Mapped[StepImpact] = mapped_column(enum_type(StepImpact, "declared_impact"), default=StepImpact.SAFE)
    estimated_essence: Mapped[int] = mapped_column(default=0)
    status: Mapped[StepStatus] = mapped_column(enum_type(StepStatus, "status"), default=StepStatus.PENDING)
    ledger_entry_id: Mapped[int | None] = mapped_column(ForeignKey("ledger_entries.id", ondelete="SET NULL"))
    job_id: Mapped[str] = mapped_column(default="")
    result_text: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")


class DivineWillForecastRow(OwnedByAccount, Base):
    __tablename__ = "divine_will_forecasts"
    __table_args__ = (at_least("epochs", 1), at_least("eta_seconds", 0))

    id: Mapped[int] = mapped_column(primary_key=True)
    cycle_id: Mapped[int | None] = mapped_column(ForeignKey("divine_will_cycles.id", ondelete="SET NULL"), index=True)
    epochs: Mapped[int]
    status: Mapped[ForecastStatus] = mapped_column(enum_type(ForecastStatus, "status"), default=ForecastStatus.QUEUED)
    eta_seconds: Mapped[int] = mapped_column(default=0)
    interventions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    report: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    job_id: Mapped[str] = mapped_column(default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created()
