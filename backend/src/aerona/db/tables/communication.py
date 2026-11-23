from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.communication import OpinionSubject, SignalKind, SignalState
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

APPROVAL_MIN = -100
APPROVAL_MAX = 100


class PublicOpinionRow(Base):
    __tablename__ = "public_opinion"
    __table_args__ = (between("approval", APPROVAL_MIN, APPROVAL_MAX), at_least("epoch", 0), Index("ix_public_opinion_subject", "subject_node_id"))

    community_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    subject_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    subject: Mapped[OpinionSubject] = mapped_column(enum_type(OpinionSubject, "subject"))
    approval: Mapped[int] = mapped_column(default=0)
    censored: Mapped[bool] = mapped_column(default=False)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CipherRow(Base):
    __tablename__ = "ciphers"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX), at_least("since_epoch", 0))

    owner_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    strength: Mapped[int] = mapped_column(default=30)
    broken_by: Mapped[list[int]] = mapped_column(JSON, default=list)
    attempts: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    break_known: Mapped[bool] = mapped_column(default=False)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SignalLinkRow(Base):
    __tablename__ = "signal_links"
    __table_args__ = (at_least("since_epoch", 0), between("condition", PERCENT_MIN, PERCENT_MAX), Index("ix_signal_links_owner", "owner_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[SignalKind] = mapped_column(enum_type(SignalKind, "kind"))
    from_region_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    to_region_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    item_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    state: Mapped[SignalState] = mapped_column(enum_type(SignalState, "state"), default=SignalState.ACTIVE)
    condition: Mapped[int] = mapped_column(default=100, server_default="100")
    jammed_epoch: Mapped[int | None]
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
