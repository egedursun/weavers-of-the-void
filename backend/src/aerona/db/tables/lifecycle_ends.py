from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, enum_type
from aerona.domain.enums.lifecycle_end import LifecycleCause, LifecycleKind, LifecycleState

LIFECYCLE_FIELDS = ("state", "cause", "idle_epochs")


class LifecycleStateRow(Base):
    __tablename__ = "lifecycle_states"
    __table_args__ = (at_least("idle_epochs", 0), at_least("since_epoch", 0), at_least("updated_epoch", 0))

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[LifecycleKind] = mapped_column(enum_type(LifecycleKind, "kind"))
    state: Mapped[LifecycleState] = mapped_column(enum_type(LifecycleState, "state"), default=LifecycleState.ACTIVE)
    cause: Mapped[LifecycleCause] = mapped_column(enum_type(LifecycleCause, "cause"), default=LifecycleCause.LIVING)
    idle_epochs: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
