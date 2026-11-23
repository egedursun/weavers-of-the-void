from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, enum_type
from aerona.domain.enums.world import WorldType
from aerona.domain.enums.world_end import WorldEnd, WorldEndCause

WORLD_END_FIELDS = ("state", "cause", "source_node_id")


class WorldEndRow(Base):
    __tablename__ = "world_ends"
    __table_args__ = (
        at_least("epoch", 0),
        at_least("lives_ended", 0),
        at_least("homeless", 0),
        at_least("anchors_lost", 0),
        at_least("routes_closed", 0),
    )

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    state: Mapped[WorldEnd] = mapped_column(enum_type(WorldEnd, "state"))
    cause: Mapped[WorldEndCause] = mapped_column(enum_type(WorldEndCause, "cause"))
    epoch: Mapped[int] = mapped_column(default=0)
    former_type: Mapped[WorldType] = mapped_column(enum_type(WorldType, "former_type"))
    new_type: Mapped[WorldType | None] = mapped_column(enum_type(WorldType, "new_type"))
    source_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    lives_ended: Mapped[int] = mapped_column(default=0)
    homeless: Mapped[int] = mapped_column(default=0)
    anchors_lost: Mapped[int] = mapped_column(default=0)
    routes_closed: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
