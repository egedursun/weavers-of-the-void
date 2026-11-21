from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.leader_cults import CultFate
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN


class LeaderCultRow(Base):
    __tablename__ = "leader_cults"
    __table_args__ = (
        between("intensity", PERCENT_MIN, PERCENT_MAX),
        between("sincerity", PERCENT_MIN, PERCENT_MAX),
        at_least("begun_epoch", 0),
        Index("ix_leader_cults_leader", "leader_node_id"),
        Index("ix_leader_cults_polity", "polity_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    leader_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    polity_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    promoters: Mapped[list[int]] = mapped_column(JSON, default=list)
    instruments: Mapped[list[str]] = mapped_column(JSON, default=list)
    intensity: Mapped[int] = mapped_column(default=20)
    sincerity: Mapped[int] = mapped_column(default=60)
    fate: Mapped[CultFate] = mapped_column(enum_type(CultFate, "fate"), default=CultFate.LIVING)
    heir_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    faith_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    begun_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
