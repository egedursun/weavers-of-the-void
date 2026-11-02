from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, enum_type
from aerona.domain.enums.world import ClimateEra


class ClimateOrderRow(Base):
    __tablename__ = "climate_orders"
    __table_args__ = (at_least("ordered_epoch", 1),)

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    era: Mapped[ClimateEra] = mapped_column(enum_type(ClimateEra, "era"))
    ordered_epoch: Mapped[int]
    son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
