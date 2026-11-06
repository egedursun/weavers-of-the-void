from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, enum_type
from aerona.domain.enums.affliction import PackageKind, Transmission


class AfflictionRow(Base):
    __tablename__ = "afflictions"
    __table_args__ = (
        at_least("stage", 0),
        at_least("since_epoch", 0),
        Index("ix_afflictions_bearer", "bearer_node_id"),
        Index("ix_afflictions_package", "package"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bearer_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    package: Mapped[PackageKind] = mapped_column(enum_type(PackageKind, "package"))
    stage: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int]
    stage_since_epoch: Mapped[int]
    transmission: Mapped[Transmission] = mapped_column(enum_type(Transmission, "transmission"))
    source_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    cured_epoch: Mapped[int | None]
    applied: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
