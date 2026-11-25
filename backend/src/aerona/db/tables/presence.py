from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, enum_type
from aerona.domain.enums.presence import PresenceEventKind, PresenceExchangeStatus, PresenceGuise, PresenceRecord, PresenceStatus


def created() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class PresenceSessionRow(Base):
    __tablename__ = "presence_sessions"
    __table_args__ = (at_least("opened_epoch", 0),)

    id: Mapped[int] = mapped_column(primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    guise: Mapped[PresenceGuise] = mapped_column(enum_type(PresenceGuise, "guise"))
    record: Mapped[PresenceRecord] = mapped_column(enum_type(PresenceRecord, "record"))
    status: Mapped[PresenceStatus] = mapped_column(enum_type(PresenceStatus, "status"), default=PresenceStatus.OPEN)
    dead_when_summoned: Mapped[bool] = mapped_column(default=False)
    title: Mapped[str] = mapped_column(default="")
    opened_epoch: Mapped[int]
    opened_at: Mapped[datetime] = created()
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PresenceExchangeRow(Base):
    __tablename__ = "presence_exchanges"
    __table_args__ = (
        UniqueConstraint("session_id", "ordinal", name="uq_presence_exchanges_ordinal"),
        at_least("ordinal", 1),
        at_least("epoch", 0),
        at_least("input_tokens", 0),
        at_least("output_tokens", 0),
        at_least("steps", 0),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("presence_sessions.id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int]
    epoch: Mapped[int]
    player_text: Mapped[str] = mapped_column(Text)
    reply_text: Mapped[str] = mapped_column(Text, default="")
    remember_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[PresenceExchangeStatus] = mapped_column(enum_type(PresenceExchangeStatus, "status"), default=PresenceExchangeStatus.RUNNING)
    error: Mapped[str] = mapped_column(Text, default="")
    model: Mapped[str] = mapped_column(default="")
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    steps: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime] = created()
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PresenceEventRow(Base):
    __tablename__ = "presence_events"
    __table_args__ = (UniqueConstraint("exchange_id", "ordinal", name="uq_presence_events_ordinal"), at_least("ordinal", 1))

    id: Mapped[int] = mapped_column(primary_key=True)
    exchange_id: Mapped[int] = mapped_column(ForeignKey("presence_exchanges.id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int]
    kind: Mapped[PresenceEventKind] = mapped_column(enum_type(PresenceEventKind, "kind"))
    tool: Mapped[str] = mapped_column(default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = created()
