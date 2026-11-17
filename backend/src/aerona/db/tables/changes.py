from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import enum_type
from aerona.domain.enums.meta import LedgerOperation
from aerona.domain.enums.modifier import ModifierOp
from aerona.domain.enums.node import ActorKind


class StateChangeRow(Base):
    __tablename__ = "state_changes"
    __table_args__ = (
        Index("ix_state_changes_row", "table_name", "row_key", "id"),
        Index("ix_state_changes_node", "node_id", "epoch"),
        Index("ix_state_changes_incident", "incident_id"),
        Index("ix_state_changes_epoch", "epoch", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    epoch: Mapped[int]
    year: Mapped[int | None]
    season: Mapped[int | None]
    day: Mapped[int | None]
    hour: Mapped[int | None]
    table_name: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    row_key: Mapped[str] = mapped_column(Text)
    node_id: Mapped[int | None]
    operation: Mapped[LedgerOperation] = mapped_column(enum_type(LedgerOperation, "operation"))
    field: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    before_number: Mapped[float | None] = mapped_column(Float)
    after_number: Mapped[float | None] = mapped_column(Float)
    before_text: Mapped[str | None] = mapped_column(Text)
    after_text: Mapped[str | None] = mapped_column(Text)
    before_node_id: Mapped[int | None]
    after_node_id: Mapped[int | None]
    actor_kind: Mapped[ActorKind] = mapped_column(enum_type(ActorKind, "actor_kind"))
    actor_node_id: Mapped[int | None]
    phase: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    step_id: Mapped[int | None] = mapped_column(ForeignKey("incident_steps.id", ondelete="SET NULL"))


class StateChangeTermRow(Base):
    __tablename__ = "state_change_terms"

    change_id: Mapped[int] = mapped_column(ForeignKey("state_changes.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(primary_key=True)
    term: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    source_node_id: Mapped[int | None]
    source_incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    op: Mapped[ModifierOp] = mapped_column(enum_type(ModifierOp, "op"))
    amount: Mapped[float] = mapped_column(Float)


class StateCheckpointRow(Base):
    __tablename__ = "state_checkpoints"
    __table_args__ = (Index("ix_state_checkpoints_epoch", "epoch", "table_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    epoch: Mapped[int]
    table_name: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    row_count: Mapped[int]
    digest: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    last_change_id: Mapped[int]
