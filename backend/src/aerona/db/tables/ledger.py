from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH, LEDGER_SUMMARY_MAX_LENGTH, NAME_MAX_LENGTH
from aerona.db.base import Base, CreatedAtMixin
from aerona.db.columns import enum_type
from aerona.db.types import PydanticJSON, UtcDateTime
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.node import ActorKind


class LedgerEntryRow(CreatedAtMixin, Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (Index("ix_ledger_entries_epoch", "epoch", "id"), Index("ix_ledger_entries_actor", "actor_node_id", "epoch"))

    id: Mapped[int] = mapped_column(primary_key=True)
    epoch: Mapped[int]
    actor_kind: Mapped[ActorKind] = mapped_column(enum_type(ActorKind, "actor_kind"))
    actor_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    actor_name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    tool: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    action_kind: Mapped[ActionKind] = mapped_column(enum_type(ActionKind, "action_kind"))
    input_summary: Mapped[str | None] = mapped_column(String(LEDGER_SUMMARY_MAX_LENGTH))
    undone: Mapped[bool] = mapped_column(default=False)
    undone_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    applied: Mapped[list[str]] = mapped_column(PydanticJSON(list[str]), default=list)
    conflicts: Mapped[list[str]] = mapped_column(PydanticJSON(list[str]), default=list)


class LedgerChangeRow(Base):
    __tablename__ = "ledger_changes"
    __table_args__ = (Index("ix_ledger_changes_row", "table_name", "row_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("ledger_entries.id", ondelete="CASCADE"), index=True)
    table_name: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    row_key: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    operation: Mapped[LedgerOperation] = mapped_column(enum_type(LedgerOperation, "operation"))
    before: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSON)
