from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import enum_type
from aerona.domain.enums.society import Commodity


class ResourceCommodityRow(Base):
    __tablename__ = "resource_commodities"

    resource_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    commodity: Mapped[Commodity] = mapped_column(enum_type(Commodity, "commodity"), index=True)
