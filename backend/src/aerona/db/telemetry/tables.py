from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Float, Index, MetaData, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH, NAME_MAX_LENGTH
from aerona.db.base import NAMING_CONVENTION
from aerona.db.columns import at_least, enum_type
from aerona.db.types import UtcDateTime
from aerona.domain.enums.telemetry import LlmCallKind, LlmCallStatus


class TelemetryBase(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class LlmCallRow(TelemetryBase):
    __tablename__ = "llm_calls"
    __table_args__ = (
        at_least("duration_ms", 0),
        at_least("attempts", 1),
        at_least("input_tokens", 0),
        at_least("output_tokens", 0),
        Index("ix_llm_calls_epoch", "epoch"),
        Index("ix_llm_calls_job", "job"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    epoch: Mapped[int | None]
    job: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    role: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    model: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    kind: Mapped[LlmCallKind] = mapped_column(enum_type(LlmCallKind, "kind"))
    status: Mapped[LlmCallStatus] = mapped_column(enum_type(LlmCallStatus, "status"))
    duration_ms: Mapped[int] = mapped_column(BigInteger)
    attempts: Mapped[int] = mapped_column(default=1)
    turns: Mapped[int | None]
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    actions: Mapped[int | None]
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), server_default=func.now())


class UsageTotalsRow(TelemetryBase):
    __tablename__ = "usage_totals"
    __table_args__ = (at_least("tokens", 0), at_least("calls", 0))

    id: Mapped[int] = mapped_column(primary_key=True)
    tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    calls: Mapped[int] = mapped_column(BigInteger, default=0)
    since: Mapped[datetime] = mapped_column(UtcDateTime(), server_default=func.now())


class LiveEventRow(TelemetryBase):
    __tablename__ = "live_events"
    __table_args__ = (Index("ix_live_events_kind", "kind", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp_ms: Mapped[int] = mapped_column(BigInteger, index=True)
    kind: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    world_key: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH), index=True)
