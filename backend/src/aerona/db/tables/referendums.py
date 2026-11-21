from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.referendums import Franchise, ReferendumCaller, ReferendumResult, ReferendumSubject


class ReferendumRow(Base):
    __tablename__ = "referendums"
    __table_args__ = (
        between("threshold_pct", PERCENT_MIN, PERCENT_MAX),
        between("yes_pct", PERCENT_MIN, PERCENT_MAX),
        between("turnout_pct", PERCENT_MIN, PERCENT_MAX),
        between("fraud", PERCENT_MIN, PERCENT_MAX),
        at_least("yes_spending", 0),
        at_least("no_spending", 0),
        at_least("called_epoch", 0),
        Index("ix_referendums_holder", "holder_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH), default="")
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    subject: Mapped[ReferendumSubject] = mapped_column(enum_type(ReferendumSubject, "subject"), default=ReferendumSubject.LAW)
    target_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    caller: Mapped[ReferendumCaller] = mapped_column(enum_type(ReferendumCaller, "caller"), default=ReferendumCaller.RULER)
    called_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    franchise: Mapped[Franchise] = mapped_column(enum_type(Franchise, "franchise"), default=Franchise.NOBLES)
    binding: Mapped[bool] = mapped_column(default=True)
    threshold_pct: Mapped[int] = mapped_column(default=50)
    yes_spending: Mapped[int] = mapped_column(default=0)
    no_spending: Mapped[int] = mapped_column(default=0)
    yes_pct: Mapped[int] = mapped_column(default=50)
    turnout_pct: Mapped[int] = mapped_column(default=0)
    fraud: Mapped[int] = mapped_column(default=0)
    result: Mapped[ReferendumResult] = mapped_column(enum_type(ReferendumResult, "result"), default=ReferendumResult.PENDING)
    ignored: Mapped[bool] = mapped_column(default=False)
    called_epoch: Mapped[int] = mapped_column(default=0)
    held_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
