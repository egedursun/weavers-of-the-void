from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, enum_type
from aerona.domain.enums.endowments import EndowmentCapital, EndowmentPurpose, EndowmentState, EndowmentTerms


class EndowmentRow(Base):
    __tablename__ = "endowments"
    __table_args__ = (
        at_least("capital", 0),
        at_least("income", 0),
        at_least("skimmed", 0),
        at_least("founded_epoch", 0),
        Index("ix_endowments_founder", "founder_node_id"),
        Index("ix_endowments_beneficiary", "beneficiary_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    founder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    beneficiary_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    trustee_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    purpose: Mapped[EndowmentPurpose] = mapped_column(enum_type(EndowmentPurpose, "purpose"), default=EndowmentPurpose.RELIEF)
    capital_kind: Mapped[EndowmentCapital] = mapped_column(enum_type(EndowmentCapital, "capital_kind"), default=EndowmentCapital.COIN)
    capital: Mapped[int] = mapped_column(default=100)
    income: Mapped[int] = mapped_column(default=0)
    skimmed: Mapped[int] = mapped_column(default=0)
    terms: Mapped[EndowmentTerms] = mapped_column(enum_type(EndowmentTerms, "terms"), default=EndowmentTerms.PERPETUAL)
    ends_epoch: Mapped[int | None]
    sheltered: Mapped[bool] = mapped_column(default=False)
    state: Mapped[EndowmentState] = mapped_column(enum_type(EndowmentState, "state"), default=EndowmentState.SERVING)
    outlived: Mapped[bool] = mapped_column(default=False)
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
