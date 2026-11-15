from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.garden import GardenKind

GARDEN_FIELDS = ("kind", "upkeep", "condition")


class GardenRow(Base):
    __tablename__ = "gardens"
    __table_args__ = (
        between("condition", 0, 100),
        at_least("upkeep", 0),
        at_least("unpaid_epochs", 0),
        at_least("founded_epoch", 0),
        Index("ix_gardens_settlement", "settlement_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    structure_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    kind: Mapped[GardenKind] = mapped_column(enum_type(GardenKind, "kind"))
    species: Mapped[list[int]] = mapped_column(JSON, default=list)
    upkeep: Mapped[int] = mapped_column(default=10)
    condition: Mapped[int] = mapped_column(default=60)
    unpaid_epochs: Mapped[int] = mapped_column(default=0)
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
