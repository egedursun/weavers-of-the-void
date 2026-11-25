from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.constants.team import AUTHOR_NAME_MAX_LENGTH
from aerona.db.authorship import account_id, account_name
from aerona.db.base import Base, CreatedAtMixin
from aerona.db.columns import at_least, enum_type
from aerona.db.types import UtcDateTime
from aerona.domain.enums.chronicle import NotificationCategory
from aerona.domain.enums.team import ProposalStatus, QueuedActSource, QueuedActStatus


class QueuedActRow(CreatedAtMixin, Base):
    __tablename__ = "queued_acts"
    __table_args__ = (at_least("queued_epoch", 0), Index("ix_queued_acts_status", "status", "id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[QueuedActSource] = mapped_column(enum_type(QueuedActSource, "source"))
    action_id: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    title: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    reason: Mapped[str | None] = mapped_column(Text)
    expected_revision: Mapped[int | None]
    author_account_id: Mapped[int | None] = mapped_column(default=account_id, index=True)
    author_name: Mapped[str | None] = mapped_column(String(AUTHOR_NAME_MAX_LENGTH), default=account_name)
    speaker_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    presence_session_id: Mapped[int | None] = mapped_column(ForeignKey("presence_sessions.id", ondelete="SET NULL"))
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("divine_will_plans.id", ondelete="SET NULL"))
    plan_ordinal: Mapped[int | None]
    queued_epoch: Mapped[int]
    status: Mapped[QueuedActStatus] = mapped_column(enum_type(QueuedActStatus, "status"), default=QueuedActStatus.QUEUED)
    result: Mapped[str] = mapped_column(Text, default="")
    applied_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    ledger_entry_id: Mapped[int | None] = mapped_column(ForeignKey("ledger_entries.id", ondelete="SET NULL"))
    cancelled_by_account_id: Mapped[int | None]
    cancelled_by_name: Mapped[str | None] = mapped_column(String(AUTHOR_NAME_MAX_LENGTH))
    conflict: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    proposal_id: Mapped[int | None] = mapped_column(ForeignKey("canon_proposals.id", ondelete="SET NULL"))


class CanonProposalRow(CreatedAtMixin, Base):
    __tablename__ = "canon_proposals"
    __table_args__ = (at_least("proposed_epoch", 0), Index("ix_canon_proposals_status", "status", "id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    action_id: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    title: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    reason: Mapped[str | None] = mapped_column(Text)
    preview: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    touches: Mapped[list[str]] = mapped_column(JSON, default=list)
    held_node_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    author_account_id: Mapped[int | None] = mapped_column(default=account_id, index=True)
    author_name: Mapped[str | None] = mapped_column(String(AUTHOR_NAME_MAX_LENGTH), default=account_name)
    proposed_epoch: Mapped[int]
    status: Mapped[ProposalStatus] = mapped_column(enum_type(ProposalStatus, "status"), default=ProposalStatus.PENDING)
    decided_by_account_id: Mapped[int | None]
    decided_by_name: Mapped[str | None] = mapped_column(String(AUTHOR_NAME_MAX_LENGTH))
    decided_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    note: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="")
    ledger_entry_id: Mapped[int | None] = mapped_column(ForeignKey("ledger_entries.id", ondelete="SET NULL"))
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("divine_will_plans.id", ondelete="SET NULL"))
    plan_ordinal: Mapped[int | None]


class NotificationReadRow(Base):
    __tablename__ = "notification_reads"

    notification_id: Mapped[int] = mapped_column(ForeignKey("notifications.id", ondelete="CASCADE"), primary_key=True)
    account_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    read_at: Mapped[datetime] = mapped_column(UtcDateTime())


class NotificationPreferenceRow(Base):
    __tablename__ = "notification_preferences"

    account_id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[NotificationCategory] = mapped_column(enum_type(NotificationCategory, "category"), primary_key=True)
    enabled: Mapped[bool]
