from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, enum_type
from aerona.domain.enums.loops import BalanceLoop


class LoopSignalRow(Base):
    __tablename__ = "loop_signals"
    __table_args__ = (at_least("epoch", 0), at_least("subject", 0))

    loop: Mapped[BalanceLoop] = mapped_column(enum_type(BalanceLoop, "loop"), primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    subject: Mapped[int] = mapped_column(primary_key=True, default=0)
    epoch: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[float]
