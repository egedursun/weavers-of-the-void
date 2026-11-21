from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import enum_type
from aerona.domain.enums.mind import Emotion


class FeelingSpreadRow(Base):
    __tablename__ = "feeling_spread"
    __table_args__ = (Index("ix_feeling_spread_settlement", "settlement_entity_id"), Index("ix_feeling_spread_household", "household_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    household_id: Mapped[int | None] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    feelings: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    leading: Mapped[Emotion | None] = mapped_column(enum_type(Emotion, "leading"))
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
