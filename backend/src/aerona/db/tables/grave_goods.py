from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import between, enum_type
from aerona.domain.enums.death_work import RemainsTreatment
from aerona.domain.enums.grave_goods import GraveGuard
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN


class GraveGoodsRow(Base):
    __tablename__ = "grave_goods"
    __table_args__ = (between("goods_value", PERCENT_MIN, PERCENT_MAX),)

    id: Mapped[int] = mapped_column(primary_key=True)
    dead_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), unique=True)
    grave_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    custom: Mapped[RemainsTreatment] = mapped_column(enum_type(RemainsTreatment, "custom"), default=RemainsTreatment.BURIAL)
    items: Mapped[list[int]] = mapped_column(JSON, default=list)
    goods_value: Mapped[int] = mapped_column(default=0)
    guard: Mapped[GraveGuard] = mapped_column(enum_type(GraveGuard, "guard"), default=GraveGuard.NONE)
    placed_epoch: Mapped[int] = mapped_column(default=0)
    robbed_epoch: Mapped[int | None]
    robber_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    found_epoch: Mapped[int | None]
    finder_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
