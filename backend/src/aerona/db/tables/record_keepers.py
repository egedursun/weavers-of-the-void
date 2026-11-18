from sqlalchemy import JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, enum_type
from aerona.domain.enums.record_keepers import RecordKeeperKind


class RecordKeeperRow(Base):
    __tablename__ = "record_keepers"
    __table_args__ = (UniqueConstraint("kind", "scope_node_id", name="uq_record_keepers_kind_scope"), at_least("since_epoch", 0))

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[RecordKeeperKind] = mapped_column(enum_type(RecordKeeperKind, "kind"))
    scope_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    keeper_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
