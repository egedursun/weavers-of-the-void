from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import between, enum_type
from aerona.domain.enums.intrigue import BeliefSource
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

SOURCE_TRUST_FIELDS = ("trust",)


class SourceTrustRow(Base):
    __tablename__ = "source_trust"
    __table_args__ = (between("trust", PERCENT_MIN, PERCENT_MAX),)

    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    source: Mapped[BeliefSource] = mapped_column(enum_type(BeliefSource, "source"), primary_key=True)
    trust: Mapped[int] = mapped_column(default=60)
    right: Mapped[int] = mapped_column(default=0)
    wrong: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
