from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between

BIOLOGY_SHARE_MAX = 500
BIOLOGY_SHARES = (
    "food_need_pct",
    "fertility_pct",
    "death_pct",
    "disease_pct",
    "morale_loss_pct",
    "fire_harm_pct",
    "storm_harm_pct",
)
BIOLOGY_FLAGS = ("breathes", "drinks", "ages")
BIOLOGY_EFFECTS = (*BIOLOGY_SHARES, *BIOLOGY_FLAGS)


class BiologyRow(Base):
    __tablename__ = "biology_variants"
    __table_args__ = (
        *(between(column, 0, BIOLOGY_SHARE_MAX) for column in BIOLOGY_SHARES),
        at_least("updated_epoch", 0),
    )

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    variants: Mapped[list[str]] = mapped_column(JSON, default=list)
    food_need_pct: Mapped[int] = mapped_column(default=100)
    fertility_pct: Mapped[int] = mapped_column(default=100)
    death_pct: Mapped[int] = mapped_column(default=100)
    disease_pct: Mapped[int] = mapped_column(default=100)
    morale_loss_pct: Mapped[int] = mapped_column(default=100)
    fire_harm_pct: Mapped[int] = mapped_column(default=100)
    storm_harm_pct: Mapped[int] = mapped_column(default=100)
    breathes: Mapped[bool] = mapped_column(default=True)
    drinks: Mapped[bool] = mapped_column(default=True)
    ages: Mapped[bool] = mapped_column(default=True)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
