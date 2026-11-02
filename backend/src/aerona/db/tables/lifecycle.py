from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base, CreatedAtMixin


class DesignatedHeirRow(CreatedAtMixin, Base):
    __tablename__ = "designated_heirs"
    __table_args__ = (CheckConstraint("ruler_entity_id <> heir_entity_id", name="not_own_heir"),)

    ruler_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    heir_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    epoch: Mapped[int]
