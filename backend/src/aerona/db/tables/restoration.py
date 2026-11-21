from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.restoration import RestorationStage


class RestorationRow(Base):
    __tablename__ = "restorations"
    __table_args__ = (
        between("memory", PERCENT_MIN, PERCENT_MAX),
        at_least("begun_epoch", 0),
        Index("ix_restorations_fallen", "fallen_polity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    fallen_polity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    claimant_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    territories: Mapped[list[int]] = mapped_column(JSON, default=list)
    bases: Mapped[list[str]] = mapped_column(JSON, default=list)
    stage: Mapped[RestorationStage] = mapped_column(enum_type(RestorationStage, "stage"), default=RestorationStage.MEMORY)
    memory: Mapped[int] = mapped_column(default=40)
    restored_polity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    begun_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
