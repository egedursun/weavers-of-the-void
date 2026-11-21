from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import between, enum_type
from aerona.domain.enums.interpretation import InterpretationFault, InterpretedEvent
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN


class InterpretationRow(Base):
    __tablename__ = "interpretations"
    __table_args__ = (between("fidelity", PERCENT_MIN, PERCENT_MAX), Index("ix_interpretations_event", "event_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    event: Mapped[InterpretedEvent] = mapped_column(enum_type(InterpretedEvent, "event"), default=InterpretedEvent.PARLEY)
    event_node_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    first_party_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    second_party_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    interpreter_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"), index=True)
    first_language_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    second_language_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    fidelity: Mapped[int] = mapped_column(default=70)
    fault: Mapped[InterpretationFault] = mapped_column(enum_type(InterpretationFault, "fault"), default=InterpretationFault.NONE)
    favoured_party_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    found: Mapped[bool] = mapped_column(default=False)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
